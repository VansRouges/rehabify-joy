"""New-thread check-in: remember the person, ask about their ailment, offer a choice."""

from __future__ import annotations

import re
from typing import Literal

from app.db.models import Patient
from app.memory.facts import get_fact

ThreadChoice = Literal["pick_up", "new_topic", "greeting", "not_better", "other"]

_BODY_PARTS: list[tuple[str, str]] = [
    ("lower back", "your lower back"),
    ("upper back", "your upper back"),
    ("shoulder", "your shoulder"),
    ("knee", "your knee"),
    ("ankle", "your ankle"),
    ("wrist", "your wrist"),
    ("neck", "your neck"),
    ("hip", "your hip"),
    ("elbow", "your elbow"),
    ("hand", "your hand"),
    ("foot", "your foot"),
    ("leg", "your leg"),
    ("arm", "your arm"),
    ("back", "your back"),
    ("head", "your head"),
]

_PICK_UP_RE = re.compile(
    r"\b("
    r"pick up|where we left off|left off|resume|"
    r"continue (the )?(questions|assessment|form|chat|from)|"
    r"carry on|old (chat|thread|conversation)|previous (chat|thread)"
    r")\b",
    re.I,
)
_NEW_TOPIC_RE = re.compile(
    r"\b("
    r"something new|new topic|something else|different (thing|issue|topic)|"
    r"another (thing|issue)|start (over|fresh)|fresh (start|chat)|talk about something"
    r")\b",
    re.I,
)
_GREETING_RE = re.compile(
    r"^(hey|hi|hello|how far|how you dey|good (morning|afternoon|evening))"
    r"[\s,!.]*(joy)?[\s,!.?]*$",
    re.I,
)
_NOT_BETTER_RE = re.compile(
    r"^\s*(no|nope|not really|not better|worse|still (hurting|bad|painful)|it'?s (not better|worse|still bad))\s*[.!]?\s*$",
    re.I,
)
_REMEMBER_RE = re.compile(r"\bremember me\b", re.I)
_CONTINUE_RE = re.compile(r"^\s*(continue|resume|pick up)\s*[.!]?\s*$", re.I)


def patient_first_name(patient: Patient) -> str | None:
    name = get_fact(patient, "name")
    if not name and patient.display_name and patient.display_name not in {"WhatsApp User", ""}:
        name = patient.display_name
    if not name:
        return None
    return str(name).split()[0]


def known_complaint(patient: Patient) -> str | None:
    complaint = get_fact(patient, "complaint")
    if complaint:
        return str(complaint).strip()
    intake = patient.intake_data if isinstance(patient.intake_data, dict) else {}
    presenting = (intake.get("complaint") or {}).get("presenting_complaint")
    if presenting:
        return str(presenting).strip()
    return None


def ailment_phrase(complaint: str | None) -> str:
    if not complaint:
        return "the pain"
    text = complaint.lower()
    for needle, phrase in _BODY_PARTS:
        if needle in text:
            return phrase
    return "the pain"


def is_returning_patient(patient: Patient, existing_session_count: int = 0) -> bool:
    if existing_session_count > 0:
        return True
    if known_complaint(patient):
        return True
    if (patient.conversation_summary or "").strip():
        return True
    if patient.intake_step and patient.intake_step not in {"start", None}:
        return True
    return False


def build_check_in(patient: Patient) -> str:
    name = patient_first_name(patient) or "there"
    ailment = ailment_phrase(known_complaint(patient))
    return (
        f"Hey {name}, how are you doing? How's {ailment} — is it better now? "
        "Would you like to pick up where we left off, or would you like to talk about something new?"
    )


def classify_thread_choice(text: str) -> ThreadChoice:
    raw = (text or "").strip()
    if not raw:
        return "other"
    if _PICK_UP_RE.search(raw) or _CONTINUE_RE.match(raw):
        return "pick_up"
    if _NEW_TOPIC_RE.search(raw):
        return "new_topic"
    if _GREETING_RE.match(raw) or _REMEMBER_RE.search(raw):
        return "greeting"
    if _NOT_BETTER_RE.match(raw):
        return "not_better"
    return "other"


def resume_lead_in(patient: Patient) -> str:
    name = patient_first_name(patient)
    if name:
        return f"Of course, {name}. Let's pick up where we left off."
    return "Of course. Let's pick up where we left off."


def still_hurting_nudge(patient: Patient) -> str:
    name = patient_first_name(patient) or "there"
    ailment = ailment_phrase(known_complaint(patient))
    return (
        f"I'm sorry {name} — I'm here with you. If {ailment} still isn't right, "
        "we can pick up where we left off, or talk about something new. Which would you prefer?"
    )
