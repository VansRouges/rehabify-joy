from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Patient
from app.utils import is_valid_phone, normalize_phone


async def get_or_create_patient_by_phone(
    db: AsyncSession,
    raw_phone: str,
    display_name: str | None = None,
) -> Patient:
    phone_input = raw_phone if raw_phone.startswith("+") else f"+{raw_phone}"
    if not is_valid_phone(phone_input):
        raise ValueError(f"Invalid phone number: {raw_phone}")

    phone = normalize_phone(phone_input)
    result = await db.execute(select(Patient).where(Patient.phone_number == phone))
    patient = result.scalar_one_or_none()

    name = (display_name or "WhatsApp User").strip()[:255]
    if patient:
        if display_name and patient.display_name in {"", "WhatsApp User"}:
            patient.display_name = name
            await db.commit()
            await db.refresh(patient)
        return patient

    patient = Patient(phone_number=phone, display_name=name)
    db.add(patient)
    await db.commit()
    await db.refresh(patient)
    return patient
