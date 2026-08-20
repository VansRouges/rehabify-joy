import uuid
from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.runtime import run_agent
from app.config import get_settings
from app.db.models import ChatSession, Message, Patient
from app.language.detect import detect_language
from app.llm.protocol import LLMError
from app.memory.audit import write_audit
from app.memory.compiler import compile_context
from app.memory.facts import facts_from_intake
from app.memory.hydrate import hydrate_session_state, maybe_compact_summary, persist_working_memory
from app.services.flow_engine import FlowResult, process_intake_message, should_run_intake
from app.services.safety import check_off_topic, check_red_flags
from app.services.session import default_session_state

settings = get_settings()


class ChatResult:
    def __init__(
        self,
        session_id: str,
        reply: str,
        mode: str,
        *,
        red_flag_triggered: bool = False,
        off_topic: bool = False,
        intake_complete: bool = False,
    ):
        self.session_id = session_id
        self.reply = reply
        self.mode = mode
        self.red_flag_triggered = red_flag_triggered
        self.off_topic = off_topic
        self.intake_complete = intake_complete


async def _persist_exchange(
    db: AsyncSession,
    patient: Patient,
    session_id: str,
    user_text: str,
    reply: str,
    *,
    red_flag_triggered: bool = False,
    message_type: str = "text",
    audio_url: str | None = None,
) -> None:
    sid = uuid.UUID(session_id)
    pid = patient.id

    result = await db.execute(
        select(ChatSession).where(ChatSession.id == sid, ChatSession.patient_id == pid)
    )
    session = result.scalar_one_or_none()

    if session is None:
        title = user_text[:80] + ("..." if len(user_text) > 80 else "")
        session = ChatSession(id=sid, patient_id=pid, title=title, mode="triage")
        db.add(session)
    elif not session.title:
        session.title = user_text[:80] + ("..." if len(user_text) > 80 else "")

    session.updated_at = datetime.now(timezone.utc)

    db.add(
        Message(
            session_id=sid,
            patient_id=pid,
            direction="in",
            content=user_text,
            message_type=message_type,
            audio_url=audio_url,
            red_flag_triggered=red_flag_triggered,
        )
    )
    db.add(
        Message(
            session_id=sid,
            patient_id=pid,
            direction="out",
            content=reply,
            message_type="text",
            red_flag_triggered=red_flag_triggered,
        )
    )
    await db.commit()


def _flow_to_chat_result(flow: FlowResult) -> ChatResult:
    return ChatResult(
        flow.session_id,
        flow.reply,
        flow.mode,
        red_flag_triggered=flow.red_flag_triggered,
        intake_complete=flow.intake_complete,
    )


def _apply_language(patient: Patient, user_text: str) -> str:
    guess = detect_language(user_text, fallback=patient.language_preference)
    if guess.confidence == "high" or not patient.language_preference:
        patient.language_preference = guess.code
    return patient.language_preference or "en"


async def process_message(
    db: AsyncSession,
    patient: Patient,
    user_text: str,
    session_id: str | None = None,
    *,
    message_type: str = "text",
    audio_url: str | None = None,
    channel: str = "web",
) -> ChatResult:
    user_text = user_text.strip()
    if not user_text:
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    sid = session_id or str(uuid.uuid4())
    pid = str(patient.id)
    language = _apply_language(patient, user_text)
    facts_from_intake(patient)

    if should_run_intake(patient):
        flow = await process_intake_message(
            db,
            patient,
            user_text,
            sid,
            message_type=message_type,
            audio_url=audio_url,
            channel=channel,
        )
        facts_from_intake(patient)
        await db.commit()
        return _flow_to_chat_result(flow)

    red_flag = check_red_flags(user_text, language)
    if red_flag.blocked:
        reply = red_flag.reply or ""
        await write_audit(
            db,
            patient_id=patient.id,
            session_id=sid,
            kind="safety",
            payload={"flag_type": red_flag.flag_type, "language": language},
        )
        await _persist_exchange(
            db, patient, sid, user_text, reply,
            red_flag_triggered=True, message_type=message_type, audio_url=audio_url,
        )
        state = await hydrate_session_state(db, patient, sid)
        state["history"].append({"role": "user", "content": user_text})
        state["history"].append({"role": "assistant", "content": reply})
        state["language"] = language
        await persist_working_memory(pid, sid, state)
        return ChatResult(sid, reply, "triage", red_flag_triggered=True)

    off_topic = check_off_topic(user_text, language)
    if off_topic.blocked:
        reply = off_topic.reply or ""
        await _persist_exchange(
            db, patient, sid, user_text, reply,
            message_type=message_type, audio_url=audio_url,
        )
        state = await hydrate_session_state(db, patient, sid)
        state["history"].append({"role": "user", "content": user_text})
        state["history"].append({"role": "assistant", "content": reply})
        state["language"] = language
        await persist_working_memory(pid, sid, state)
        return ChatResult(sid, reply, "triage", off_topic=True)

    state = await hydrate_session_state(db, patient, sid)
    compiled = compile_context(patient, state.get("history") or [], max_turns=settings.max_history_turns)

    try:
        reply = await run_agent(db, patient, compiled, user_text, sid)
    except LLMError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    state["history"].append({"role": "user", "content": user_text})
    state["history"].append({"role": "assistant", "content": reply})
    state["language"] = language
    maybe_compact_summary(patient, state["history"])
    await persist_working_memory(pid, sid, state)

    await _persist_exchange(
        db, patient, sid, user_text, reply,
        message_type=message_type, audio_url=audio_url,
    )

    return ChatResult(sid, reply, state.get("mode") or default_session_state()["mode"])
