from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from app.config import get_settings
from app.db.models import Message, Patient
from app.memory.facts import digest_from_facts
from app.services.session import (
    default_session_state,
    get_session_state,
    save_session_state,
    trim_history,
)

settings = get_settings()


def session_redis_key(patient_id: str, session_id: str) -> str:
    return f"joy:session:{patient_id}:{session_id}"


def _messages_to_history(rows: list[Message]) -> list[dict[str, str]]:
    history: list[dict[str, str]] = []
    for row in rows:
        role = "user" if row.direction == "in" else "assistant"
        if row.content:
            history.append({"role": role, "content": row.content})
    return history


async def hydrate_session_state(
    db: AsyncSession,
    patient: Patient,
    session_id: str,
) -> dict[str, Any]:
    """Load working memory from Redis, or rebuild the last turns from Postgres."""
    pid = str(patient.id)
    key = session_redis_key(pid, session_id)
    state = await get_session_state(key)
    if state and state.get("history"):
        return state

    sid = uuid.UUID(session_id)
    result = await db.execute(
        select(Message)
        .where(Message.session_id == sid, Message.patient_id == patient.id)
        .order_by(Message.created_at.desc())
        .limit(settings.max_history_turns * 2)
    )
    rows = list(reversed(result.scalars().all()))
    state = state or default_session_state()
    state["patient_id"] = pid
    state["language"] = patient.language_preference or state.get("language")
    state["history"] = _messages_to_history(rows)
    await save_session_state(key, state)
    return state


async def persist_working_memory(
    patient_id: str,
    session_id: str,
    state: dict[str, Any],
) -> None:
    state["history"] = trim_history(state.get("history") or [], settings.max_history_turns)
    await save_session_state(session_redis_key(patient_id, session_id), state)


def maybe_compact_summary(patient: Patient, history: list[dict[str, str]]) -> None:
    """When the live thread is long, store a short digest for later sessions."""
    if len(history) < settings.max_history_turns * 2:
        return
    digest = digest_from_facts(patient)
    if digest:
        patient.conversation_summary = digest[:2000]
        flag_modified(patient, "conversation_summary")
