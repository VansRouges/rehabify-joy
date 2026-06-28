import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, File, Form, Header, HTTPException, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.patients import get_patient_or_404
from app.config import get_settings
from app.db.database import get_db
from app.db.models import ChatSession, Message
from app.services.chat_service import process_message
from app.services.gemini import GeminiError
from app.services.storage import upload_audio
from app.services.transcription import transcribe_audio
from app.services.session import default_session_state, save_session_state

router = APIRouter(prefix="/chat", tags=["chat"])
settings = get_settings()

MAX_AUDIO_BYTES = 10 * 1024 * 1024  # 10 MB


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=4000)
    session_id: str | None = None


class ChatResponse(BaseModel):
    session_id: str
    reply: str
    mode: str
    red_flag_triggered: bool = False
    off_topic: bool = False
    transcription: str | None = None


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
    message_type: str
    audio_url: str | None
    red_flag_triggered: bool
    created_at: datetime


class SessionDetail(BaseModel):
    id: str
    title: str | None
    mode: str
    triage_complete: bool
    messages: list[MessageOut]


async def _require_patient_id(x_patient_id: str | None = Header(default=None)) -> str:
    if not x_patient_id:
        raise HTTPException(status_code=401, detail="Patient ID required. Please register first.")
    return x_patient_id


@router.post("", response_model=ChatResponse)
async def send_message(
    body: ChatRequest,
    patient_id: str = Depends(_require_patient_id),
    db: AsyncSession = Depends(get_db),
) -> ChatResponse:
    patient = await get_patient_or_404(patient_id, db)
    result = await process_message(db, patient, body.message, body.session_id)
    return ChatResponse(
        session_id=result.session_id,
        reply=result.reply,
        mode=result.mode,
        red_flag_triggered=result.red_flag_triggered,
        off_topic=result.off_topic,
    )


@router.post("/voice", response_model=ChatResponse)
async def send_voice_message(
    file: UploadFile = File(...),
    session_id: str | None = Form(default=None),
    duration_seconds: float | None = Form(default=None),
    patient_id: str = Depends(_require_patient_id),
    db: AsyncSession = Depends(get_db),
) -> ChatResponse:
    if duration_seconds is not None and duration_seconds > settings.max_voice_seconds:
        raise HTTPException(
            status_code=400,
            detail=f"Voice note must be {settings.max_voice_seconds} seconds or less",
        )

    content_type = file.content_type or "audio/webm"
    if not content_type.startswith("audio/"):
        raise HTTPException(status_code=400, detail="File must be an audio recording")

    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Empty audio file")
    if len(data) > MAX_AUDIO_BYTES:
        raise HTTPException(status_code=400, detail="Audio file too large")

    patient = await get_patient_or_404(patient_id, db)

    audio_url: str | None = None
    try:
        audio_url = upload_audio(data, content_type, patient_id)
    except Exception:
        # Continue without storage if bucket fails — transcription still works
        audio_url = None

    try:
        transcription = await transcribe_audio(data, content_type)
    except GeminiError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    result = await process_message(
        db,
        patient,
        transcription,
        session_id,
        message_type="voice",
        audio_url=audio_url,
    )

    return ChatResponse(
        session_id=result.session_id,
        reply=result.reply,
        mode=result.mode,
        red_flag_triggered=result.red_flag_triggered,
        off_topic=result.off_topic,
        transcription=transcription,
    )


@router.post("/sessions", response_model=SessionSummary)
async def create_session(
    patient_id: str = Depends(_require_patient_id),
    db: AsyncSession = Depends(get_db),
) -> SessionSummary:
    patient = await get_patient_or_404(patient_id, db)
    session = ChatSession(patient_id=patient.id, mode="triage")
    db.add(session)
    await db.commit()
    await db.refresh(session)

    state = default_session_state()
    state["patient_id"] = patient_id
    await save_session_state(f"joy:session:{patient_id}:{session.id}", state)

    return SessionSummary(
        id=str(session.id),
        title=session.title,
        mode=session.mode,
        created_at=session.created_at,
        updated_at=session.updated_at,
    )


@router.get("/sessions", response_model=list[SessionSummary])
async def list_sessions(
    patient_id: str = Depends(_require_patient_id),
    db: AsyncSession = Depends(get_db),
) -> list[SessionSummary]:
    patient = await get_patient_or_404(patient_id, db)
    result = await db.execute(
        select(ChatSession)
        .where(ChatSession.patient_id == patient.id)
        .order_by(ChatSession.updated_at.desc())
        .limit(50)
    )
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
async def get_session(
    session_id: str,
    patient_id: str = Depends(_require_patient_id),
    db: AsyncSession = Depends(get_db),
) -> SessionDetail:
    patient = await get_patient_or_404(patient_id, db)
    try:
        sid = uuid.UUID(session_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid session ID") from exc

    result = await db.execute(
        select(ChatSession).where(ChatSession.id == sid, ChatSession.patient_id == patient.id)
    )
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
                message_type=m.message_type,
                audio_url=m.audio_url,
                red_flag_triggered=m.red_flag_triggered,
                created_at=m.created_at,
            )
            for m in messages
        ],
    )
