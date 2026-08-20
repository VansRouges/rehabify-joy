from __future__ import annotations

from typing import Any

from sqlalchemy.orm.attributes import flag_modified

from app.db.models import Patient

FACT_KEYS = frozenset(
    {
        "name",
        "region",
        "city",
        "complaint",
        "intake_complete",
        "red_flag",
        "language",
        "consent",
    }
)


def _facts(patient: Patient) -> dict[str, Any]:
    data = patient.known_facts
    if not isinstance(data, dict):
        return {}
    return dict(data)


def get_fact(patient: Patient, key: str) -> Any:
    facts = _facts(patient)
    if key in facts:
        return facts[key]
    custom = facts.get("custom")
    if isinstance(custom, dict):
        return custom.get(key)
    return None


def remember_fact(patient: Patient, key: str, value: Any) -> dict[str, Any]:
    """Write a durable fact onto the patient. Returns the updated map."""
    clean_key = str(key).strip()[:80]
    if not clean_key:
        return _facts(patient)
    facts = _facts(patient)
    if clean_key in FACT_KEYS:
        facts[clean_key] = value
    else:
        custom = facts.get("custom")
        if not isinstance(custom, dict):
            custom = {}
        custom[clean_key] = value
        facts["custom"] = custom
    patient.known_facts = facts
    flag_modified(patient, "known_facts")
    if clean_key == "name" and value:
        patient.display_name = str(value).strip()[:255]
    if clean_key == "language" and value:
        patient.language_preference = str(value).strip()[:10]
    if clean_key == "region" and value:
        patient.region = str(value).strip()[:100]
    return facts


def facts_from_intake(patient: Patient) -> dict[str, Any]:
    """Sync structured facts from completed / in-progress intake_data."""
    facts = _facts(patient)
    intake = patient.intake_data if isinstance(patient.intake_data, dict) else {}
    profile = intake.get("profile") or {}
    complaint = intake.get("complaint") or {}
    if profile.get("first_name"):
        facts["name"] = str(profile["first_name"]).strip()
    if complaint.get("presenting_complaint"):
        facts["complaint"] = str(complaint["presenting_complaint"]).strip()
    if patient.consent_given:
        facts["consent"] = True
    if patient.intake_step in {"cultural_complete", "complete"}:
        facts["intake_complete"] = True
    if intake.get("red_flag_triggered"):
        facts["red_flag"] = True
    if patient.language_preference:
        facts["language"] = patient.language_preference
    if patient.display_name and patient.display_name not in {"WhatsApp User", ""}:
        facts.setdefault("name", patient.display_name.split()[0])
    patient.known_facts = facts
    flag_modified(patient, "known_facts")
    return facts


def digest_from_facts(patient: Patient) -> str:
    facts = _facts(patient)
    parts: list[str] = []
    name = facts.get("name") or patient.display_name
    if name and name not in {"WhatsApp User", ""}:
        parts.append(f"Patient is {name}")
    if facts.get("complaint"):
        parts.append(f"complaint: {facts['complaint']}")
    if facts.get("intake_complete"):
        parts.append("intake complete")
    if facts.get("red_flag"):
        parts.append("red flag previously triggered")
    lang = facts.get("language") or patient.language_preference
    if lang:
        parts.append(f"language {lang}")
    custom = facts.get("custom")
    if isinstance(custom, dict):
        extras = [f"{k}={v}" for k, v in list(custom.items())[:6]]
        parts.extend(extras)
    return "; ".join(parts) if parts else ""
