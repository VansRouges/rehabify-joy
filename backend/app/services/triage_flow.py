"""Layer 1 intake flow definitions — consent through presenting complaint (step 5)."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any, Callable

CONSENT_LINKS = """1. Privacy Policy — how we store and use your health information.
   https://physioaroundme.com/privacy

2. Terms of Service — what you agree to by using Rehabify.
   https://physioaroundme.com/terms

3. Cookie Policy — how we use data to improve your experience.
   https://physioaroundme.com/cookies

4. Informed Consent — your health information will be used to match you with the right specialist and improve our platform. It will never be sold. It will never be shared without your consent."""

CONSENT_INTRO = """Hello! My name is Joy — I am here to help you understand what is going on with your health and connect you with the right specialist.

Before we begin, I need to share a few important things with you:

{links}

Please reply YES to confirm you have read and agree to these.
Reply NO if you have any questions first."""

CONSENT_REMINDER = """Have you read the above and do you agree to continue? Please reply YES to continue or NO if you have questions."""

CONSENT_NO_REPLY = """No problem — take your time. If you have questions about how we use your information, visit physioaroundme.com/privacy or reply here and I'll help.

When you're ready to continue, reply YES."""

PROFILE_COMPLETE_MSG = "Great — your profile is set up. Now let me understand what has been going on with you."

CLINICAL_HISTORY_COMPLETE_MSG = (
    "Thank you for sharing your history — that helps your specialist a lot. "
    "Now I want to understand what has been going on with you."
)

COMPLAINT_COMPLETE_MSG = (
    "Thank you for sharing all of that with me — I know some of those questions were detailed. "
    "You've completed the main assessment questions. Next we'll run a quick safety check "
    "before I summarise everything and recommend next steps."
)

PAIN_KEYWORDS = re.compile(
    r"\b(pain|ache|aching|hurt|hurting|sore|stiff|stiffness|discomfort|back|knee|"
    r"shoulder|neck|ankle|wrist|hip|joint)\b",
    re.I,
)
NEURO_KEYWORDS = re.compile(
    r"\b(numb|numbness|tingl|weakness|weak|balance|stroke|parkinson|paralys|paralyz|"
    r"can't walk|cannot walk|grip|neuro|sciatica|foot drop)\b",
    re.I,
)

YES_RE = re.compile(r"^(yes|y|yeah|yep|ok|okay|sure|agree|i agree|confirmed?)$", re.I)
NO_RE = re.compile(r"^(no|n|nope|not yet)$", re.I)


@dataclass(frozen=True)
class StepDef:
    id: str
    prompt: str
    field: str | None = None
    section: str = "intake"


def _parse_dob(raw: str) -> tuple[date | None, str | None]:
    text = raw.strip()
    for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y"):
        try:
            dob = datetime.strptime(text, fmt).date()
            break
        except ValueError:
            dob = None
    else:
        return None, "Please enter your date of birth as DD/MM/YYYY (for example, 15/03/1990)."

    today = date.today()
    age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
    if age < 16:
        return None, "You must be at least 16 years old to use Rehabify."
    if dob > today:
        return None, "That date doesn't look right. Please check and try again."
    return dob, None


def _parse_email(raw: str) -> tuple[str | None, str | None]:
    text = raw.strip()
    if text.lower() in {"skip", "none", "no", "n/a", "na"}:
        return "", None
    if re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", text):
        return text.lower(), None
    return None, "Please enter a valid email address, or reply SKIP if you'd rather not share one."


def _parse_gender(raw: str) -> tuple[str | None, str | None]:
    text = raw.strip().lower()
    mapping = {
        "male": "male",
        "m": "male",
        "man": "male",
        "female": "female",
        "f": "female",
        "woman": "female",
        "prefer not to say": "prefer_not_to_say",
        "prefer not": "prefer_not_to_say",
        "no": "prefer_not_to_say",
    }
    if text in mapping:
        return mapping[text], None
    return None, "Please reply with male, female, or prefer not to say."


def _parse_consultation_pref(raw: str) -> tuple[str | None, str | None]:
    text = raw.strip().lower()
    if any(w in text for w in ("virtual", "online", "video", "tele", "call")):
        return "virtual", None
    if any(w in text for w in ("home", "in-person", "in person", "visit", "house")):
        return "in_person", None
    if any(w in text for w in ("either", "both", "any", "doesn't matter", "doesnt matter")):
        return "either", None
    return None, "Would you prefer virtual (video), in-person (home visit), or either works for you?"


def _parse_phone_confirm(raw: str, expected: str) -> tuple[bool | None, str | None]:
    text = raw.strip().lower()
    if YES_RE.match(text) or text == expected.lower().replace("+", ""):
        return True, None
    if NO_RE.match(text):
        return False, "No problem — please type the correct WhatsApp number including country code (e.g. +234...)."
    digits = re.sub(r"\D", "", raw)
    if len(digits) >= 10:
        return True, None
    return None, f"Is {expected} the correct number for WhatsApp? Please reply YES or type the correct number."


def _parse_severity(raw: str) -> tuple[int | None, str | None]:
    match = re.search(r"\b(10|[0-9])\b", raw.strip())
    if not match:
        return None, "Please give a number from 1 to 10."
    value = int(match.group(1))
    if 1 <= value <= 10:
        return value, None
    return None, "Please give a number from 1 to 10."


PROFILE_STEPS: list[StepDef] = [
    StepDef("profile_first_name", "What is your first name?", "first_name", "profile"),
    StepDef("profile_last_name", "And your last name?", "last_name", "profile"),
    StepDef(
        "profile_gender",
        "How do you identify — male, female, or would you prefer not to say?",
        "gender",
        "profile",
    ),
    StepDef(
        "profile_dob",
        "What is your date of birth? (DD/MM/YYYY)",
        "date_of_birth",
        "profile",
    ),
    StepDef(
        "profile_email",
        "What is your email address? We will send your booking confirmation there. Reply SKIP if you'd rather not.",
        "email",
        "profile",
    ),
    StepDef("profile_country", "Which country are you currently in?", "country", "profile"),
    StepDef("profile_state", "Which state?", "state", "profile"),
    StepDef("profile_city", "Which city or area within that state?", "city", "profile"),
    StepDef(
        "profile_phone_confirm",
        "Confirm your WhatsApp number — is it {phone}?",
        "phone_confirmed",
        "profile",
    ),
    StepDef(
        "profile_consultation_preference",
        "How would you prefer to speak with your specialist — virtual, in-person, or either works for you?",
        "consultation_preference",
        "profile",
    ),
]

CLINICAL_STEPS: list[StepDef] = [
    StepDef(
        "clinical_comorbidities",
        "Do you have any existing medical conditions — for example, diabetes, high blood pressure, heart disease, osteoporosis, or anything else you are currently being managed for?",
        "comorbidities",
        "clinical_history",
    ),
    StepDef(
        "clinical_surgical_history",
        "Have you had any surgeries in the past? If yes — what type and when?",
        "surgical_history",
        "clinical_history",
    ),
    StepDef(
        "clinical_hospitalisation",
        "Have you ever been admitted to hospital? If yes — what for and when?",
        "hospitalisation_history",
        "clinical_history",
    ),
    StepDef(
        "clinical_medications",
        "Are you currently taking any medication — prescribed or over the counter?",
        "current_medications",
        "clinical_history",
    ),
    StepDef(
        "clinical_allergies",
        "Do you have any known allergies — to medication, materials or anything else?",
        "allergies",
        "clinical_history",
    ),
    StepDef(
        "clinical_occupation",
        "What do you do for work — and does your job involve a lot of sitting, standing, lifting or physical activity?",
        "occupation",
        "clinical_history",
    ),
    StepDef(
        "clinical_activity_level",
        "How would you describe your general activity level — mostly active, mostly sedentary, or somewhere in between?",
        "activity_level",
        "clinical_history",
    ),
    StepDef(
        "clinical_lifestyle",
        "Do you smoke, drink alcohol, or use any recreational substances? You do not have to answer if you prefer not to.",
        "lifestyle_factors",
        "clinical_history",
    ),
    StepDef(
        "clinical_travel",
        "Have you travelled outside your city or country recently — in the last three months?",
        "recent_travel",
        "clinical_history",
    ),
    StepDef(
        "clinical_family_history",
        "Does anyone in your immediate family have a history of arthritis, osteoporosis, neurological conditions, or autoimmune disease?",
        "family_history",
        "clinical_history",
    ),
]

PAIN_STEPS: list[StepDef] = [
    StepDef("complaint_pain_onset", "When did this pain first start?", "pain_onset", "complaint"),
    StepDef(
        "complaint_pain_onset_type",
        "Did it come on suddenly or gradually?",
        "pain_onset_type",
        "complaint",
    ),
    StepDef(
        "complaint_pain_pattern",
        "Is the pain there all the time, or does it come and go?",
        "pain_pattern",
        "complaint",
    ),
    StepDef(
        "complaint_pain_quality",
        "How would you describe the pain — is it sharp, burning, aching, throbbing, stabbing, or something else?",
        "pain_quality",
        "complaint",
    ),
    StepDef(
        "complaint_pain_severity_now",
        "On a scale of 1 to 10 — where 1 is barely there and 10 is unbearable — how would you rate it right now?",
        "pain_severity_now",
        "complaint",
    ),
    StepDef(
        "complaint_pain_severity_worst",
        "And at its worst — what number would you give it?",
        "pain_severity_worst",
        "complaint",
    ),
    StepDef(
        "complaint_pain_location",
        "Where exactly is the pain? Can you point to it or describe the location?",
        "pain_location",
        "complaint",
    ),
    StepDef(
        "complaint_pain_radiation",
        "Does the pain spread anywhere — for example, down your arm, leg, or anywhere else?",
        "pain_radiation",
        "complaint",
    ),
    StepDef(
        "complaint_pain_aggravating",
        "What makes it worse — movement, sitting, standing, sleeping, lifting, or something else?",
        "pain_aggravating_factors",
        "complaint",
    ),
    StepDef(
        "complaint_pain_relieving",
        "What makes it better — rest, movement, heat, cold, medication, or nothing?",
        "pain_relieving_factors",
        "complaint",
    ),
    StepDef(
        "complaint_pain_previous",
        "Has this ever happened before? If yes — how was it managed?",
        "pain_previous_episodes",
        "complaint",
    ),
]

NEURO_STEPS: list[StepDef] = [
    StepDef(
        "complaint_neuro_location",
        "Where exactly are you feeling the numbness or weakness — which part of your body?",
        "neuro_location",
        "complaint",
    ),
    StepDef(
        "complaint_neuro_onset",
        "When did this start — and did it come on suddenly or gradually?",
        "neuro_onset",
        "complaint",
    ),
    StepDef(
        "complaint_neuro_pattern",
        "Is it constant or does it come and go?",
        "neuro_pattern",
        "complaint",
    ),
    StepDef(
        "complaint_neuro_progression",
        "Has it been getting worse, staying the same, or improving since it started?",
        "neuro_progression",
        "complaint",
    ),
    StepDef(
        "complaint_neuro_functional",
        "Has it affected your ability to walk, grip things, or do normal daily activities?",
        "neuro_functional_impact",
        "complaint",
    ),
    StepDef(
        "complaint_neuro_falls",
        "Have you had a fall or any loss of balance recently?",
        "falls_history",
        "complaint",
    ),
]

FUNCTIONAL_STEPS: list[StepDef] = [
    StepDef(
        "complaint_functional_limitations",
        "How much is this getting in the way of your normal life — work, sleep, caring for your family, or anything that matters to you?",
        "functional_limitations",
        "complaint",
    ),
    StepDef(
        "complaint_patient_goal",
        "If we fixed this completely — what is the one thing you most want to go back to doing?",
        "patient_goal",
        "complaint",
    ),
]

STEP_BY_ID: dict[str, StepDef] = {
    s.id: s
    for s in PROFILE_STEPS + CLINICAL_STEPS + PAIN_STEPS + NEURO_STEPS + FUNCTIONAL_STEPS
}

INTAKE_COMPLETE_STEP = "complaint_complete"


def default_intake_data() -> dict[str, Any]:
    return {
        "profile": {},
        "clinical_history": {},
        "complaint": {},
        "pathways": [],
        "pathway_queue": [],
    }


def detect_pathways(text: str) -> list[str]:
    has_pain = bool(PAIN_KEYWORDS.search(text))
    has_neuro = bool(NEURO_KEYWORDS.search(text))
    pathways: list[str] = []
    if has_pain:
        pathways.append("pain")
    if has_neuro:
        pathways.append("neuro")
    return pathways


def validate_step(step_id: str, raw: str, intake_data: dict[str, Any], phone: str) -> tuple[Any, str | None]:
    text = raw.strip()
    if not text:
        return None, "I didn't catch that — could you try again?"

    if step_id == "profile_gender":
        return _parse_gender(text)
    if step_id == "profile_dob":
        dob, err = _parse_dob(text)
        if err:
            return None, err
        return dob.isoformat(), None
    if step_id == "profile_email":
        return _parse_email(text)
    if step_id == "profile_consultation_preference":
        return _parse_consultation_pref(text)
    if step_id == "profile_phone_confirm":
        ok, err = _parse_phone_confirm(text, phone)
        if err:
            return None, err
        return ok, None
    if step_id in {"complaint_pain_severity_now", "complaint_pain_severity_worst"}:
        return _parse_severity(text)

    if step_id == "profile_first_name" and len(text) < 1:
        return None, "Please tell me your first name."
    if step_id == "profile_last_name" and len(text) < 1:
        return None, "Please tell me your last name."

    return text, None


def prompt_for_step(step_id: str, intake_data: dict[str, Any], phone: str) -> str:
    if step_id == "consent_pending":
        return CONSENT_REMINDER
    if step_id == "complaint_opening":
        return (
            "Now I want to understand what has been going on with you. "
            "In your own words — what is the main thing that has been bothering you?"
        )
    if step_id == "complaint_pathway_clarify":
        return (
            "Thanks for sharing that. Is it mainly pain or discomfort, "
            "or more numbness, tingling, or weakness — or both?"
        )

    step = STEP_BY_ID.get(step_id)
    if not step:
        return "Let's continue — could you answer my last question?"
    prompt = step.prompt
    if "{phone}" in prompt:
        prompt = prompt.format(phone=phone)
    return prompt


def _acknowledge(name: str | None, answer: str) -> str:
    first = (name or "there").split()[0]
    short = answer.strip()
    if len(short) > 60:
        short = short[:57] + "..."
    return f"Thanks, {first} — I've noted that."


def next_step_id(current: str, intake_data: dict[str, Any]) -> str:
    if current == "consent_pending":
        return PROFILE_STEPS[0].id

    for i, step in enumerate(PROFILE_STEPS):
        if step.id == current:
            return PROFILE_STEPS[i + 1].id if i + 1 < len(PROFILE_STEPS) else CLINICAL_STEPS[0].id

    for i, step in enumerate(CLINICAL_STEPS):
        if step.id == current:
            return CLINICAL_STEPS[i + 1].id if i + 1 < len(CLINICAL_STEPS) else "complaint_opening"

    if current == "complaint_opening":
        pathways = intake_data.get("pathways") or []
        queue = list(pathways)
        intake_data["pathway_queue"] = queue
        if not queue:
            return "complaint_pathway_clarify"
        return _first_pathway_step(queue[0])

    if current == "complaint_pathway_clarify":
        queue = intake_data.get("pathway_queue") or []
        if not queue:
            return "complaint_pathway_clarify"
        return _first_pathway_step(queue[0])

    if current in {s.id for s in PAIN_STEPS}:
        return _advance_in_list(current, PAIN_STEPS, intake_data)

    if current in {s.id for s in NEURO_STEPS}:
        return _advance_in_list(current, NEURO_STEPS, intake_data)

    if current == "complaint_functional_limitations":
        return FUNCTIONAL_STEPS[1].id

    if current == "complaint_patient_goal":
        return INTAKE_COMPLETE_STEP

    return INTAKE_COMPLETE_STEP


def _first_pathway_step(pathway: str) -> str:
    if pathway == "pain":
        return PAIN_STEPS[0].id
    if pathway == "neuro":
        return NEURO_STEPS[0].id
    return FUNCTIONAL_STEPS[0].id


def _advance_in_list(current: str, steps: list[StepDef], intake_data: dict[str, Any]) -> str:
    ids = [s.id for s in steps]
    idx = ids.index(current)
    if idx + 1 < len(steps):
        return steps[idx + 1].id

    queue: list[str] = list(intake_data.get("pathway_queue") or [])
    if queue and queue[0] == ("pain" if steps is PAIN_STEPS else "neuro"):
        queue.pop(0)
        intake_data["pathway_queue"] = queue
    if queue:
        return _first_pathway_step(queue[0])
    return FUNCTIONAL_STEPS[0].id


def is_intake_in_progress(step: str | None) -> bool:
    if not step:
        return True
    return step not in {INTAKE_COMPLETE_STEP, "complete"}


def section_for_step(step_id: str) -> str:
    if step_id in STEP_BY_ID:
        return STEP_BY_ID[step_id].section
    if step_id.startswith("profile_"):
        return "profile"
    if step_id.startswith("clinical_"):
        return "clinical_history"
    return "complaint"
