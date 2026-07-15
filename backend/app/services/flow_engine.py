"""Orchestrates Layer 1 intake: consent → profile → clinical history → complaint."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import ChatSession, Patient
from app.services.triage_flow import (
    CLINICAL_HISTORY_COMPLETE_MSG,
    COMPLAINT_COMPLETE_MSG,
    CONSENT_INTRO,
    CONSENT_LINKS,
    CONSENT_NO_REPLY,
    INTAKE_COMPLETE_STEP,
    NO_RE,
    PROFILE_COMPLETE_MSG,
    YES_RE,
    _acknowledge,
    default_intake_data,
    detect_pathways,
    is_intake_in_progress,
    next_step_id,
    prompt_for_step,
    section_for_step,
    validate_step,
)

INITIAL_STEP = "consent_pending"


@dataclass
class FlowResult:
    session_id: str
    reply: str
    mode: str = "triage"
    flow_step: str = ""
    intake_complete: bool = False


def _patient_first_name(patient: Patient, intake_data: dict[str, Any]) -> str | None:
    profile = intake_data.get("profile") or {}
    if profile.get("first_name"):
        return profile["first_name"]
    if patient.display_name and patient.display_name != "WhatsApp User":
        return patient.display_name.split()[0]
    return None


def _ensure_intake(patient: Patient) -> dict[str, Any]:
    if patient.intake_data and isinstance(patient.intake_data, dict):
        data = patient.intake_data
        for key in ("profile", "clinical_history", "complaint"):
            data.setdefault(key, {})
        data.setdefault("pathways", [])
        data.setdefault("pathway_queue", [])
        return data
    return default_intake_data()


async def _persist_messages(
    db: AsyncSession,
    patient: Patient,
    session_id: str,
    user_text: str,
    reply: str,
    *,
    message_type: str = "text",
    audio_url: str | None = None,
) -> None:
    from sqlalchemy import select

    sid = uuid.UUID(session_id)
    result = await db.execute(
        select(ChatSession).where(ChatSession.id == sid, ChatSession.patient_id == patient.id)
    )
    session = result.scalar_one_or_none()
    if session is None:
        title = user_text[:80] + ("..." if len(user_text) > 80 else "")
        session = ChatSession(id=sid, patient_id=patient.id, title=title, mode="triage")
        db.add(session)
    elif not session.title:
        session.title = user_text[:80] + ("..." if len(user_text) > 80 else "")

    session.updated_at = datetime.now(timezone.utc)
    triage = _ensure_intake(patient)
    session.triage_summary = triage

    from app.db.models import Message

    db.add(
        Message(
            session_id=sid,
            patient_id=patient.id,
            direction="in",
            content=user_text,
            message_type=message_type,
            audio_url=audio_url,
        )
    )
    db.add(
        Message(
            session_id=sid,
            patient_id=patient.id,
            direction="out",
            content=reply,
            message_type="text",
        )
    )
    await db.commit()


async def _save_patient_intake(
    db: AsyncSession,
    patient: Patient,
    *,
    step: str,
    intake_data: dict[str, Any],
    consent_given: bool | None = None,
) -> None:
    patient.intake_step = step
    patient.intake_data = intake_data
    if consent_given is not None:
        patient.consent_given = consent_given
        if consent_given:
            patient.consent_at = datetime.now(timezone.utc)
    profile = intake_data.get("profile") or {}
    if profile.get("first_name") and profile.get("last_name"):
        patient.display_name = f"{profile['first_name']} {profile['last_name']}".strip()
    elif profile.get("first_name"):
        patient.display_name = profile["first_name"]
    if profile.get("state"):
        patient.region = profile["state"]
    await db.commit()
    await db.refresh(patient)


def _store_field(intake_data: dict[str, Any], step_id: str, value: Any) -> None:
    section = section_for_step(step_id)
    if section == "profile":
        key = step_id.replace("profile_", "")
        intake_data.setdefault("profile", {})[key] = value
    elif section == "clinical_history":
        key = step_id.replace("clinical_", "")
        intake_data.setdefault("clinical_history", {})[key] = value
    elif section == "complaint":
        if step_id == "complaint_opening":
            intake_data.setdefault("complaint", {})["presenting_complaint"] = value
            intake_data["pathways"] = detect_pathways(str(value))
        elif step_id == "complaint_pathway_clarify":
            pathways = detect_pathways(str(value))
            if pathways:
                intake_data["pathways"] = pathways
        else:
            key = step_id.replace("complaint_", "")
            intake_data.setdefault("complaint", {})[key] = value


async def process_intake_message(
    db: AsyncSession,
    patient: Patient,
    user_text: str,
    session_id: str | None = None,
    *,
    message_type: str = "text",
    audio_url: str | None = None,
    channel: str = "web",
) -> FlowResult:
    user_text = user_text.strip()
    sid = session_id or str(uuid.uuid4())
    intake_data = _ensure_intake(patient)
    step = patient.intake_step or INITIAL_STEP
    name = _patient_first_name(patient, intake_data)

    if step == INTAKE_COMPLETE_STEP or step == "complete":
        return FlowResult(
            session_id=sid,
            reply=(
                "You've already completed the assessment questions. "
                "We'll continue with your safety check and recommendations soon."
            ),
            flow_step=step,
            intake_complete=True,
        )

    # --- Consent gate ---
    if not patient.consent_given:
        if step == INITIAL_STEP and not patient.intake_step:
            intro = CONSENT_INTRO.format(links=CONSENT_LINKS)
            if name:
                intro = f"Hello {name}! " + intro[len("Hello! ") :]
            reply = intro
            await _save_patient_intake(db, patient, step=INITIAL_STEP, intake_data=intake_data)
            await _persist_messages(db, patient, sid, user_text, reply, message_type=message_type, audio_url=audio_url)
            return FlowResult(session_id=sid, reply=reply, flow_step=INITIAL_STEP)

        if YES_RE.match(user_text):
            await _save_patient_intake(
                db, patient, step="profile_first_name", intake_data=intake_data, consent_given=True
            )
            reply = f"Thank you — I appreciate that.\n\n{prompt_for_step('profile_first_name', intake_data, patient.phone_number)}"
            await _persist_messages(db, patient, sid, user_text, reply, message_type=message_type, audio_url=audio_url)
            return FlowResult(session_id=sid, reply=reply, flow_step="profile_first_name")

        if NO_RE.match(user_text):
            await _save_patient_intake(db, patient, step=INITIAL_STEP, intake_data=intake_data)
            await _persist_messages(db, patient, sid, user_text, CONSENT_NO_REPLY, message_type=message_type, audio_url=audio_url)
            return FlowResult(session_id=sid, reply=CONSENT_NO_REPLY, flow_step=INITIAL_STEP)

        reminder = CONSENT_INTRO.format(links=CONSENT_LINKS) if not patient.intake_step else prompt_for_step("consent_pending", intake_data, patient.phone_number)
        await _save_patient_intake(db, patient, step=INITIAL_STEP, intake_data=intake_data)
        await _persist_messages(db, patient, sid, user_text, reminder, message_type=message_type, audio_url=audio_url)
        return FlowResult(session_id=sid, reply=reminder, flow_step=INITIAL_STEP)

    # --- Profile, clinical, complaint steps ---
    if step == "complaint_opening":
        _store_field(intake_data, step, user_text)
        nxt = next_step_id(step, intake_data)
        ack = _acknowledge(name, user_text)
        if nxt == "complaint_pathway_clarify":
            reply = f"{ack}\n\n{prompt_for_step(nxt, intake_data, patient.phone_number)}"
        else:
            reply = f"{ack}\n\n{prompt_for_step(nxt, intake_data, patient.phone_number)}"
        await _save_patient_intake(db, patient, step=nxt, intake_data=intake_data)
        await _persist_messages(db, patient, sid, user_text, reply, message_type=message_type, audio_url=audio_url)
        return FlowResult(session_id=sid, reply=reply, flow_step=nxt)

    if step == "complaint_pathway_clarify":
        pathways = detect_pathways(user_text)
        if not pathways:
            err = "Could you tell me if it's mainly pain, or numbness/tingling/weakness, or both?"
            await _persist_messages(db, patient, sid, user_text, err, message_type=message_type, audio_url=audio_url)
            return FlowResult(session_id=sid, reply=err, flow_step=step)
        intake_data["pathways"] = pathways
        intake_data["pathway_queue"] = list(pathways)
        nxt = next_step_id(step, intake_data)
        reply = f"{_acknowledge(name, user_text)}\n\n{prompt_for_step(nxt, intake_data, patient.phone_number)}"
        await _save_patient_intake(db, patient, step=nxt, intake_data=intake_data)
        await _persist_messages(db, patient, sid, user_text, reply, message_type=message_type, audio_url=audio_url)
        return FlowResult(session_id=sid, reply=reply, flow_step=nxt)

    value, error = validate_step(step, user_text, intake_data, patient.phone_number)
    if error:
        retry = f"{error}\n\n{prompt_for_step(step, intake_data, patient.phone_number)}"
        await _persist_messages(db, patient, sid, user_text, retry, message_type=message_type, audio_url=audio_url)
        return FlowResult(session_id=sid, reply=retry, flow_step=step)

    _store_field(intake_data, step, value)
    nxt = next_step_id(step, intake_data)

    transition = ""
    if step == "profile_consultation_preference":
        transition = f"\n\n{PROFILE_COMPLETE_MSG}"
    elif step == "clinical_family_history":
        transition = f"\n\n{CLINICAL_HISTORY_COMPLETE_MSG}"
    elif step == "complaint_patient_goal":
        nxt = INTAKE_COMPLETE_STEP
        transition = f"\n\n{COMPLAINT_COMPLETE_MSG}"

    if nxt == INTAKE_COMPLETE_STEP:
        reply = f"{_acknowledge(name, user_text)}{transition}"
        await _save_patient_intake(db, patient, step=INTAKE_COMPLETE_STEP, intake_data=intake_data)
        await _persist_messages(db, patient, sid, user_text, reply, message_type=message_type, audio_url=audio_url)
        return FlowResult(session_id=sid, reply=reply, flow_step=INTAKE_COMPLETE_STEP, intake_complete=True)

    reply = f"{_acknowledge(name, user_text)}{transition}\n\n{prompt_for_step(nxt, intake_data, patient.phone_number)}"
    await _save_patient_intake(db, patient, step=nxt, intake_data=intake_data)
    await _persist_messages(db, patient, sid, user_text, reply, message_type=message_type, audio_url=audio_url)
    return FlowResult(session_id=sid, reply=reply, flow_step=nxt)


def should_run_intake(patient: Patient) -> bool:
    if patient.consent_given and patient.intake_step in {INTAKE_COMPLETE_STEP, "complete"}:
        return False
    return is_intake_in_progress(patient.intake_step) or not patient.consent_given
