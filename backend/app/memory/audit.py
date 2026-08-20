from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import AuditEvent


async def write_audit(
    db: AsyncSession,
    *,
    patient_id: uuid.UUID,
    kind: str,
    payload: dict,
    session_id: str | None = None,
    commit: bool = False,
) -> None:
    sid = uuid.UUID(session_id) if session_id else None
    db.add(
        AuditEvent(
            patient_id=patient_id,
            session_id=sid,
            kind=kind,
            payload=payload,
            created_at=datetime.now(timezone.utc),
        )
    )
    if commit:
        await db.commit()
