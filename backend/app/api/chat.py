import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.db.models import ChatSession, Message
from app.services.gemini import GeminiError, generate_reply
from app.services.safety import check_off_topic, check_red_flags
from app.services.session import (
    default_session_state,
    get_session_state,
    save_session_state,
    trim_history,
)

router = APIRouter(prefix="/chat", tags=["chat"])


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=4000)
    session_id: str | None = None


class ChatResponse(BaseModel):
    session_id: str
    reply: str
    mode: str
    red_flag_triggered: bool = False
    off_topic: bool = False


class SessionSummary(BaseModel):
    id: str
    title: str | None
    mode: str
    created_at: datetime
    updated_at: datetime


class MessageOut(BaseModel):
    id: str
    direction: str
    content: str
    red_flag_triggered: bool
    created_at: datetime


class SessionDetail(BaseModel):
    id: str
    title: str | None
    mode: str
    triage_complete: bool
    messages: list[MessageOut]


@router.post("", response_model=ChatResponse)
async def send_message(body: ChatRequest, db: AsyncSession = Depends(get_db)) -> ChatResponse:
    session_id = body.session_id or str(uuid.uuid4())
    user_text = body.message.strip()

    red_flag = check_red_flags(user_text)
    if red_flag.blocked:
        reply = red_flag.reply or ""
        await _persist_exchange(db, session_id, user_text, reply, red_flag_triggered=True)
        state = await _load_or_create_state(session_id)
        state["history"].append({"role": "user", "content": user_text})
        state["history"].append({"role": "assistant", "content": reply})
        state["history"] = trim_history(state["history"], 15)
        await save_session_state(session_id, state)
        return ChatResponse(
            session_id=session_id,
            reply=reply,
            mode=state.get("mode", "triage"),
            red_flag_triggered=True,
        )

    off_topic = check_off_topic(user_text)
    if off_topic.blocked:
        reply = off_topic.reply or ""
        await _persist_exchange(db, session_id, user_text, reply)
        state = await _load_or_create_state(session_id)
        state["history"].append({"role": "user", "content": user_text})
        state["history"].append({"role": "assistant", "content": reply})
        state["history"] = trim_history(state["history"], 15)
        await save_session_state(session_id, state)
        return ChatResponse(
            session_id=session_id,
            reply=reply,
            mode=state.get("mode", "triage"),
            off_topic=True,
        )

    state = await _load_or_create_state(session_id)

    try:
        reply = await generate_reply(state["history"], user_text)
    except GeminiError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    state["history"].append({"role": "user", "content": user_text})
    state["history"].append({"role": "assistant", "content": reply})
    state["history"] = trim_history(state["history"], 15)
    await save_session_state(session_id, state)

    await _persist_exchange(db, session_id, user_text, reply)

    return ChatResponse(
        session_id=session_id,
        reply=reply,
        mode=state.get("mode", "triage"),
    )


@router.post("/sessions", response_model=SessionSummary)
async def create_session(db: AsyncSession = Depends(get_db)) -> SessionSummary:
    session = ChatSession(mode="triage")
    db.add(session)
    await db.commit()
    await db.refresh(session)

    state = default_session_state()
    await save_session_state(str(session.id), state)

    return SessionSummary(
        id=str(session.id),
        title=session.title,
        mode=session.mode,
        created_at=session.created_at,
        updated_at=session.updated_at,
    )


@router.get("/sessions", response_model=list[SessionSummary])
async def list_sessions(db: AsyncSession = Depends(get_db)) -> list[SessionSummary]:
    result = await db.execute(select(ChatSession).order_by(ChatSession.updated_at.desc()).limit(50))
    sessions = result.scalars().all()
    return [
        SessionSummary(
            id=str(s.id),
            title=s.title,
            mode=s.mode,
            created_at=s.created_at,
            updated_at=s.updated_at,
        )
        for s in sessions
    ]


@router.get("/sessions/{session_id}", response_model=SessionDetail)
async def get_session(session_id: str, db: AsyncSession = Depends(get_db)) -> SessionDetail:
    try:
        sid = uuid.UUID(session_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid session ID") from exc

    result = await db.execute(select(ChatSession).where(ChatSession.id == sid))
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    msg_result = await db.execute(
        select(Message).where(Message.session_id == sid).order_by(Message.created_at.asc())
    )
    messages = msg_result.scalars().all()

    return SessionDetail(
        id=str(session.id),
        title=session.title,
        mode=session.mode,
        triage_complete=session.triage_complete,
        messages=[
            MessageOut(
                id=str(m.id),
                direction=m.direction,
                content=m.content,
                red_flag_triggered=m.red_flag_triggered,
                created_at=m.created_at,
            )
            for m in messages
        ],
    )


async def _load_or_create_state(session_id: str) -> dict:
    state = await get_session_state(session_id)
    if state is None:
        state = default_session_state()
        await save_session_state(session_id, state)
    return state


async def _persist_exchange(
    db: AsyncSession,
    session_id: str,
    user_text: str,
    reply: str,
    *,
    red_flag_triggered: bool = False,
) -> None:
    try:
        sid = uuid.UUID(session_id)
    except ValueError:
        return

    result = await db.execute(select(ChatSession).where(ChatSession.id == sid))
    session = result.scalar_one_or_none()

    if session is None:
        title = user_text[:80] + ("..." if len(user_text) > 80 else "")
        session = ChatSession(id=sid, title=title, mode="triage")
        db.add(session)
    elif not session.title:
        session.title = user_text[:80] + ("..." if len(user_text) > 80 else "")

    session.updated_at = datetime.now(timezone.utc)

    db.add(Message(session_id=sid, direction="in", content=user_text, red_flag_triggered=red_flag_triggered))
    db.add(Message(session_id=sid, direction="out", content=reply, red_flag_triggered=red_flag_triggered))
    await db.commit()
