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
from app.services.flow_engine import (
    FlowResult,
    patient_needs_intake,
    pending_intake_prompt,
    process_intake_message,
    session_owns_intake,
)
from app.services.safety import check_off_topic, check_red_flags
from app.services.session import default_session_state
from app.services.thread_opening import (
    build_check_in,
    classify_thread_choice,
    is_returning_patient,
    resume_lead_in,
    still_hurting_nudge,
)

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


async def _earliest_session_id(db: AsyncSession, patient: Patient) -> str | None:
    result = await db.execute(
        select(ChatSession.id)
        .where(ChatSession.patient_id == patient.id)
        .order_by(ChatSession.created_at.asc())
        .limit(1)
    )
    row = result.scalar_one_or_none()
    return str(row) if row else None


async def _should_run_intake_here(
    db: AsyncSession,
    patient: Patient,
    session_id: str,
    *,
    channel: str,
) -> bool:
    needs = patient_needs_intake(patient)
    earliest = await _earliest_session_id(db, patient)
    run, owner = session_owns_intake(
        needs_intake=needs,
        intake_session_id=patient.intake_session_id,
        current_session_id=session_id,
        earliest_session_id=earliest,
        channel=channel,
    )
    if owner:
        owner_uuid = uuid.UUID(owner)
        if patient.intake_session_id != owner_uuid:
            patient.intake_session_id = owner_uuid
    return run


def _is_fresh_thread(history: list) -> bool:
    return not any(item.get("role") == "user" for item in history or [])


async def _count_sessions(db: AsyncSession, patient: Patient) -> int:
    result = await db.execute(select(ChatSession.id).where(ChatSession.patient_id == patient.id))
    return len(result.scalars().all())


async def start_thread(db: AsyncSession, patient: Patient) -> tuple[ChatSession, str | None]:
    """Open a new web thread. Returning patients get a caring check-in first."""
    facts_from_intake(patient)
    existing = await _count_sessions(db, patient)
    session = ChatSession(patient_id=patient.id, mode="companion")
    db.add(session)
    await db.flush()

    opening: str | None = None
    state = default_session_state()
    state["patient_id"] = str(patient.id)
    state["mode"] = "companion"

    if is_returning_patient(patient, existing):
        opening = build_check_in(patient)
        session.title = "Check-in"
        db.add(
            Message(
                session_id=session.id,
                patient_id=patient.id,
                direction="out",
                content=opening,
                message_type="text",
            )
        )
        state["history"] = [{"role": "assistant", "content": opening}]
        state["awaiting_thread_choice"] = True

    await persist_working_memory(str(patient.id), str(session.id), state)
    await db.commit()
    await db.refresh(session)
    return session, opening


async def _resume_questionnaire(
    db: AsyncSession,
    patient: Patient,
    session_id: str,
    user_text: str,
    *,
    message_type: str = "text",
    audio_url: str | None = None,
) -> ChatResult:
    patient.intake_session_id = uuid.UUID(session_id)
    question = pending_intake_prompt(patient)
    if question:
        reply = f"{resume_lead_in(patient)}\n\n{question}"
        mode = "triage"
    else:
        reply = (
            f"{resume_lead_in(patient)} We already finished the assessment questions. "
            "Tell me how you've been managing, and we'll take it from there."
        )
        mode = "companion"
    await _persist_exchange(
        db, patient, session_id, user_text, reply,
        message_type=message_type, audio_url=audio_url,
    )
    state = await hydrate_session_state(db, patient, session_id)
    state["awaiting_thread_choice"] = False
    state["history"].append({"role": "user", "content": user_text})
    state["history"].append({"role": "assistant", "content": reply})
    state["mode"] = mode
    await persist_working_memory(str(patient.id), session_id, state)
    return ChatResult(session_id, reply, mode)


async def _reply_and_remember(
    db: AsyncSession,
    patient: Patient,
    session_id: str,
    user_text: str,
    reply: str,
    state: dict,
    *,
    message_type: str = "text",
    audio_url: str | None = None,
    awaiting: bool | None = None,
    mode: str = "companion",
) -> ChatResult:
    if awaiting is not None:
        state["awaiting_thread_choice"] = awaiting
    state["history"] = list(state.get("history") or [])
    state["history"].append({"role": "user", "content": user_text})
    state["history"].append({"role": "assistant", "content": reply})
    state["mode"] = mode
    await persist_working_memory(str(patient.id), session_id, state)
    await _persist_exchange(
        db, patient, session_id, user_text, reply,
        message_type=message_type, audio_url=audio_url,
    )
    return ChatResult(session_id, reply, mode)


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

    if await _should_run_intake_here(db, patient, sid, channel=channel):
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
    state["language"] = language
    history = state.get("history") or []
    awaiting = bool(state.get("awaiting_thread_choice"))
    existing_count = await _count_sessions(db, patient)
    returning = is_returning_patient(patient, existing_count)
    fresh = _is_fresh_thread(history)
    choice = classify_thread_choice(user_text)

    if channel == "web" and (awaiting or (returning and fresh)):
        if choice == "pick_up":
            return await _resume_questionnaire(
                db, patient, sid, user_text,
                message_type=message_type, audio_url=audio_url,
            )
        if choice == "not_better":
            return await _reply_and_remember(
                db, patient, sid, user_text, still_hurting_nudge(patient), state,
                message_type=message_type, audio_url=audio_url, awaiting=True,
            )
        if choice == "new_topic":
            state["awaiting_thread_choice"] = False
        elif awaiting and choice == "other":
            state["awaiting_thread_choice"] = False
        else:
            return await _reply_and_remember(
                db, patient, sid, user_text, build_check_in(patient), state,
                message_type=message_type, audio_url=audio_url, awaiting=True,
            )

    compiled = compile_context(
        patient,
        state.get("history") or [],
        max_turns=settings.max_history_turns,
        intake_open_elsewhere=patient_needs_intake(patient),
        new_thread=fresh,
    )

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
