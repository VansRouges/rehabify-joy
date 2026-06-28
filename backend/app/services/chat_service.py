import uuid
from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import ChatSession, Message, Patient
from app.services.gemini import GeminiError, generate_reply
from app.services.safety import check_off_topic, check_red_flags
from app.services.session import (
    default_session_state,
    get_session_state,
    save_session_state,
    trim_history,
)
from app.config import get_settings

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
    ):
        self.session_id = session_id
        self.reply = reply
        self.mode = mode
        self.red_flag_triggered = red_flag_triggered
        self.off_topic = off_topic


def _session_redis_key(patient_id: str, session_id: str) -> str:
    return f"joy:session:{patient_id}:{session_id}"


async def _load_or_create_state(patient_id: str, session_id: str) -> dict:
    key = _session_redis_key(patient_id, session_id)
    state = await get_session_state(key)
    if state is None:
        state = default_session_state()
        state["patient_id"] = patient_id
        await save_session_state(key, state)
    return state


async def _save_state(patient_id: str, session_id: str, state: dict) -> None:
    state["history"] = trim_history(state["history"], settings.max_history_turns)
    await save_session_state(_session_redis_key(patient_id, session_id), state)


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

    result = await db.execute(select(ChatSession).where(ChatSession.id == sid))
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


async def process_message(
    db: AsyncSession,
    patient: Patient,
    user_text: str,
    session_id: str | None = None,
    *,
    message_type: str = "text",
    audio_url: str | None = None,
) -> ChatResult:
    user_text = user_text.strip()
    if not user_text:
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    sid = session_id or str(uuid.uuid4())
    pid = str(patient.id)

    red_flag = check_red_flags(user_text)
    if red_flag.blocked:
        reply = red_flag.reply or ""
        await _persist_exchange(
            db, patient, sid, user_text, reply,
            red_flag_triggered=True, message_type=message_type, audio_url=audio_url,
        )
        state = await _load_or_create_state(pid, sid)
        state["history"].append({"role": "user", "content": user_text})
        state["history"].append({"role": "assistant", "content": reply})
        await _save_state(pid, sid, state)
        return ChatResult(sid, reply, state.get("mode", "triage"), red_flag_triggered=True)

    off_topic = check_off_topic(user_text)
    if off_topic.blocked:
        reply = off_topic.reply or ""
        await _persist_exchange(
            db, patient, sid, user_text, reply,
            message_type=message_type, audio_url=audio_url,
        )
        state = await _load_or_create_state(pid, sid)
        state["history"].append({"role": "user", "content": user_text})
        state["history"].append({"role": "assistant", "content": reply})
        await _save_state(pid, sid, state)
        return ChatResult(sid, reply, state.get("mode", "triage"), off_topic=True)

    state = await _load_or_create_state(pid, sid)

    try:
        reply = await generate_reply(state["history"], user_text)
    except GeminiError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    state["history"].append({"role": "user", "content": user_text})
    state["history"].append({"role": "assistant", "content": reply})
    await _save_state(pid, sid, state)

    await _persist_exchange(
        db, patient, sid, user_text, reply,
        message_type=message_type, audio_url=audio_url,
    )

    return ChatResult(sid, reply, state.get("mode", "triage"))
