import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.db.models import Patient
from app.utils import get_client_ip, is_valid_phone, normalize_phone

router = APIRouter(prefix="/patients", tags=["patients"])


class RegisterRequest(BaseModel):
    phone_number: str = Field(..., min_length=7, max_length=20)
    display_name: str = Field(..., min_length=1, max_length=255)


class PatientOut(BaseModel):
    patient_id: str
    phone_number: str
    display_name: str


def _record_ip(patient: Patient, ip: str) -> None:
    if not ip or ip == "unknown":
        return
    patient.last_ip_address = ip
    ips: list[str] = list(patient.ip_addresses or [])
    if ip not in ips:
        ips.append(ip)
    patient.ip_addresses = ips


@router.post("/register", response_model=PatientOut)
async def register_patient(
    body: RegisterRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> PatientOut:
    if not is_valid_phone(body.phone_number):
        raise HTTPException(status_code=400, detail="Invalid phone number")

    phone = normalize_phone(body.phone_number)
    ip = get_client_ip(request)
    name = body.display_name.strip()

    result = await db.execute(select(Patient).where(Patient.phone_number == phone))
    patient = result.scalar_one_or_none()

    if patient:
        patient.display_name = name
        patient.updated_at = datetime.now(timezone.utc)
        _record_ip(patient, ip)
    else:
        patient = Patient(
            phone_number=phone,
            display_name=name,
            last_ip_address=ip if ip != "unknown" else None,
            ip_addresses=[ip] if ip != "unknown" else [],
        )
        db.add(patient)

    await db.commit()
    await db.refresh(patient)

    return PatientOut(
        patient_id=str(patient.id),
        phone_number=patient.phone_number,
        display_name=patient.display_name,
    )


async def get_patient_or_404(patient_id: str, db: AsyncSession) -> Patient:
    try:
        pid = uuid.UUID(patient_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid patient ID") from exc

    result = await db.execute(select(Patient).where(Patient.id == pid))
    patient = result.scalar_one_or_none()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    return patient
