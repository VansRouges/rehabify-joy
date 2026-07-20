"""Orchestrates Layer 1 intake (PRD v2 health-first order)."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import ChatSession, Message, Patient
from app.services.triage_flow import (
    COMPLAINT_OPENING,
    CULTURAL_COMPLETE_MSG,
    CULTURAL_STEPS,
    FLOW_VERSION,
    INITIAL_STEP,
    INTAKE_COMPLETE_STEP,
    LIGHT_CONSENT_BLOCKED,
    NAME_PROMPT,
    OLD_FLOW_STEPS,
    RED_FLAG_BY_ID,
    acknowledge,
    default_intake_data,
    detect_pathways,
    evaluate_red_flag_answer,
    is_intake_in_progress,
    next_step_id,
    parse_consent,
    prompt_for_step,
    section_for_step,
    validate_step,
)


@dataclass
class FlowResult:
    session_id: str
    reply: str
    mode: str = "triage"
    flow_step: str = ""
    intake_complete: bool = False
    red_flag_triggered: bool = False


def _patient_first_name(patient: Patient, intake_data: dict[str, Any]) -> str | None:
    profile = intake_data.get("profile") or {}
    if profile.get("first_name"):
        return str(profile["first_name"]).split()[0]
    if patient.display_name and patient.display_name not in {"WhatsApp User", ""}:
        return patient.display_name.split()[0]
    return None


def _ensure_intake(patient: Patient) -> dict[str, Any]:
    if patient.intake_data and isinstance(patient.intake_data, dict):
        data = dict(patient.intake_data)
        for key in ("profile", "clinical_history", "complaint", "red_flags", "cultural"):
            data.setdefault(key, {})
        data.setdefault("pathways", [])
        data.setdefault("pathway_queue", [])
        data.setdefault("flow_version", FLOW_VERSION)
        return data
    return default_intake_data()


def _needs_flow_reset(patient: Patient, intake_data: dict[str, Any]) -> bool:
    if intake_data.get("flow_version") != FLOW_VERSION:
        return True
    if patient.intake_step in OLD_FLOW_STEPS:
        return True
    return False


def _reset_for_new_flow(patient: Patient) -> dict[str, Any]:
    data = default_intake_data()
    patient.consent_given = False
    patient.consent_at = None
    patient.intake_step = None
    return data


async def _persist_messages(
    db: AsyncSession,
    patient: Patient,
    session_id: str,
    user_text: str,
    reply: str,
    *,
    message_type: str = "text",
    audio_url: str | None = None,
    red_flag_triggered: bool = False,
) -> None:
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
    session.triage_summary = _ensure_intake(patient)

    db.add(
        Message(
            session_id=sid,
            patient_id=patient.id,
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
            patient_id=patient.id,
            direction="out",
            content=reply,
            message_type="text",
            red_flag_triggered=red_flag_triggered,
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
    intake_data["flow_version"] = FLOW_VERSION
    patient.intake_step = step
    patient.intake_data = intake_data
    if consent_given is not None:
        patient.consent_given = consent_given
        if consent_given:
            patient.consent_at = datetime.now(timezone.utc)
    profile = intake_data.get("profile") or {}
    if profile.get("first_name"):
        patient.display_name = str(profile["first_name"]).strip()
    await db.commit()
    await db.refresh(patient)


def _store_field(intake_data: dict[str, Any], step_id: str, value: Any) -> None:
    section = section_for_step(step_id)
    if step_id == "ask_name":
        intake_data.setdefault("profile", {})["first_name"] = value
        return
    if section == "profile":
        intake_data.setdefault("profile", {})[step_id.replace("profile_", "")] = value
    elif section == "clinical_history":
        intake_data.setdefault("clinical_history", {})[step_id.replace("clinical_", "")] = value
    elif section == "cultural":
        intake_data.setdefault("cultural", {})[step_id.replace("cultural_", "")] = value
    elif section == "red_flags":
        field = RED_FLAG_BY_ID[step_id].field
        intake_data.setdefault("red_flags", {})[field] = value
    elif section == "complaint":
        if step_id == "complaint_opening":
            intake_data.setdefault("complaint", {})["presenting_complaint"] = value
            intake_data["pathways"] = detect_pathways(str(value))
        elif step_id == "complaint_pathway_clarify":
            pathways = detect_pathways(str(value))
            if pathways:
                intake_data["pathways"] = pathways
                intake_data["pathway_queue"] = list(pathways)
        else:
            intake_data.setdefault("complaint", {})[step_id.replace("complaint_", "")] = value


async def _reply(
    db: AsyncSession,
    patient: Patient,
    sid: str,
    user_text: str,
    reply: str,
    step: str,
    *,
    message_type: str = "text",
    audio_url: str | None = None,
    intake_complete: bool = False,
    red_flag_triggered: bool = False,
) -> FlowResult:
    await _persist_messages(
        db,
        patient,
        sid,
        user_text,
        reply,
        message_type=message_type,
        audio_url=audio_url,
        red_flag_triggered=red_flag_triggered,
    )
    return FlowResult(
        session_id=sid,
        reply=reply,
        flow_step=step,
        intake_complete=intake_complete,
        red_flag_triggered=red_flag_triggered,
    )


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

    if _needs_flow_reset(patient, intake_data):
        intake_data = _reset_for_new_flow(patient)
        await _save_patient_intake(db, patient, step=INITIAL_STEP, intake_data=intake_data)

    step = patient.intake_step or INITIAL_STEP
    name = _patient_first_name(patient, intake_data)

    if step in {INTAKE_COMPLETE_STEP, "complete"}:
        return await _reply(
            db,
            patient,
            sid,
            user_text,
            (
                "You've already completed the assessment questions. "
                "We'll continue with your summary and next steps soon."
            ),
            step,
            message_type=message_type,
            audio_url=audio_url,
            intake_complete=True,
        )

    if step == "red_flag_stopped":
        return await _reply(
            db,
            patient,
            sid,
            user_text,
            (
                "Your safety comes first. Please get urgent medical care now. "
                "Once you've been seen, come back to me and we'll continue from there."
            ),
            step,
            message_type=message_type,
            audio_url=audio_url,
            red_flag_triggered=True,
        )

    # --- Step 1: Name ---
    # First contact: always ask for a name (do not treat "hi" as a name).
    if step == "start":
        await _save_patient_intake(db, patient, step="ask_name", intake_data=intake_data)
        return await _reply(
            db, patient, sid, user_text, NAME_PROMPT, "ask_name",
            message_type=message_type, audio_url=audio_url,
        )

    if step == "ask_name":
        value, error = validate_step("ask_name", user_text, intake_data, patient.phone_number)
        if error or value is None:
            return await _reply(
                db, patient, sid, user_text, error or NAME_PROMPT, "ask_name",
                message_type=message_type, audio_url=audio_url,
            )
        _store_field(intake_data, "ask_name", value)
        name = str(value).split()[0]
        nxt = "light_consent"
        await _save_patient_intake(db, patient, step=nxt, intake_data=intake_data)
        reply = prompt_for_step(nxt, intake_data, patient.phone_number, name=name)
        return await _reply(
            db, patient, sid, user_text, reply, nxt,
            message_type=message_type, audio_url=audio_url,
        )

    # --- Step 2: Light consent ---
    if step == "light_consent":
        verdict = parse_consent(user_text)
        if verdict == "yes":
            await _save_patient_intake(
                db, patient, step="complaint_opening", intake_data=intake_data, consent_given=True
            )
            return await _reply(
                db, patient, sid, user_text, COMPLAINT_OPENING, "complaint_opening",
                message_type=message_type, audio_url=audio_url,
            )
        return await _reply(
            db, patient, sid, user_text, LIGHT_CONSENT_BLOCKED, "light_consent",
            message_type=message_type, audio_url=audio_url,
        )

    # If somehow past name without consent, force light consent
    if not patient.consent_given:
        await _save_patient_intake(db, patient, step="light_consent", intake_data=intake_data)
        reply = prompt_for_step("light_consent", intake_data, patient.phone_number, name=name)
        return await _reply(
            db, patient, sid, user_text, reply, "light_consent",
            message_type=message_type, audio_url=audio_url,
        )

    # --- Step 3: Presenting complaint ---
    if step == "complaint_opening":
        _store_field(intake_data, step, user_text)
        nxt = next_step_id(step, intake_data)
        reply = f"{acknowledge(name)}\n\n{prompt_for_step(nxt, intake_data, patient.phone_number, name=name)}"
        await _save_patient_intake(db, patient, step=nxt, intake_data=intake_data)
        return await _reply(
            db, patient, sid, user_text, reply, nxt,
            message_type=message_type, audio_url=audio_url,
        )

    if step == "complaint_pathway_clarify":
        pathways = detect_pathways(user_text)
        if not pathways:
            err = "Could you tell me if it's mainly pain, or numbness/tingling/weakness, or both?"
            return await _reply(
                db, patient, sid, user_text, err, step,
                message_type=message_type, audio_url=audio_url,
            )
        intake_data["pathways"] = pathways
        intake_data["pathway_queue"] = list(pathways)
        nxt = next_step_id(step, intake_data)
        reply = f"{acknowledge(name)}\n\n{prompt_for_step(nxt, intake_data, patient.phone_number, name=name)}"
        await _save_patient_intake(db, patient, step=nxt, intake_data=intake_data)
        return await _reply(
            db, patient, sid, user_text, reply, nxt,
            message_type=message_type, audio_url=audio_url,
        )

    # --- Deep-dive, red flags, clinical history, cultural calibration ---
    value, error = validate_step(step, user_text, intake_data, patient.phone_number)
    if error:
        retry = f"{error}\n\n{prompt_for_step(step, intake_data, patient.phone_number, name=name)}"
        return await _reply(
            db, patient, sid, user_text, retry, step,
            message_type=message_type, audio_url=audio_url,
        )

    _store_field(intake_data, step, value)

    if step in RED_FLAG_BY_ID:
        triggered, emergency_reply, flag_type = evaluate_red_flag_answer(
            step, bool(value), intake_data
        )
        if triggered and emergency_reply:
            intake_data["red_flag_triggered"] = True
            intake_data["red_flag_type"] = flag_type
            stop_step = "red_flag_stopped"
            reply = (
                "What you have described sounds serious and needs urgent medical attention. "
                f"{emergency_reply}"
            )
            await _save_patient_intake(db, patient, step=stop_step, intake_data=intake_data)
            return await _reply(
                db, patient, sid, user_text, reply, stop_step,
                message_type=message_type, audio_url=audio_url, red_flag_triggered=True,
            )

    nxt = next_step_id(step, intake_data)
    transition = ""
    if step == CULTURAL_STEPS[-1].id:
        nxt = INTAKE_COMPLETE_STEP
        transition = f"\n\n{CULTURAL_COMPLETE_MSG}"

    if nxt == INTAKE_COMPLETE_STEP:
        reply = f"{acknowledge(name)}{transition}"
        await _save_patient_intake(db, patient, step=INTAKE_COMPLETE_STEP, intake_data=intake_data)
        return await _reply(
            db, patient, sid, user_text, reply, INTAKE_COMPLETE_STEP,
            message_type=message_type, audio_url=audio_url, intake_complete=True,
        )

    reply = (
        f"{acknowledge(name)}{transition}\n\n"
        f"{prompt_for_step(nxt, intake_data, patient.phone_number, name=name)}"
    )
    await _save_patient_intake(db, patient, step=nxt, intake_data=intake_data)
    return await _reply(
        db, patient, sid, user_text, reply, nxt,
        message_type=message_type, audio_url=audio_url,
    )


def should_run_intake(patient: Patient) -> bool:
    intake_data = patient.intake_data if isinstance(patient.intake_data, dict) else {}
    if intake_data.get("flow_version") != FLOW_VERSION:
        return True
    if patient.intake_step in {"red_flag_stopped"}:
        return True
    if patient.intake_step in {INTAKE_COMPLETE_STEP, "complete"}:
        return False
    return is_intake_in_progress(patient.intake_step) or not patient.consent_given
