"""Layer 1 intake flow — PRD v2 health-first order.

Order: name → light consent → complaint → deep-dive → red flags →
clinical history → cultural calibration.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Literal

FLOW_VERSION = 2

NAME_PROMPT = "Hi, I'm Joy. What can I call you?"

LIGHT_CONSENT_TEMPLATE = (
    "Nice to meet you, {name}. I'm Joy — I'll help you figure out what's been "
    "going on and get you to the right specialist. What you share stays between "
    "us and is only used for your care. Reply YES when you're ready."
)

LIGHT_CONSENT_BLOCKED = (
    "I need your yes before we go further — your privacy matters, and I only "
    "use what you share to get you the right care.\n\n"
    "When you're ready, reply YES (for example: yes, or yes I do)."
)

COMPLAINT_OPENING = (
    "I'm here with you. Tell me — what has been going on? "
    "What is the main thing that has been bothering you?"
)

PATHWAY_CLARIFY = (
    "I hear you. Is it mainly pain or discomfort, "
    "or more numbness, tingling, or weakness — or both?"
)

CULTURAL_COMPLETE_MSG = (
    "Thank you for trusting me with all of that — I know some of those questions "
    "were a lot. Let me walk you through what I think is the best next step."
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

# Explicit refusal / non-consent
CONSENT_NO_RE = re.compile(
    r"\b(no|nope|nah|not yet|don'?t|do not|refuse|disagree|won'?t|"
    r"cannot|can'?t|never)\b",
    re.I,
)
# Affirmative consent — matches "yes", "yes i consent", "yes i do", "i agree", etc.
CONSENT_YES_RE = re.compile(
    r"^\s*(yes|yeah|yep|yup|ya|yah|ok|okay|sure|alright|all right|"
    r"i\s+(do|consent|agree|accept|confirm)|"
    r"yes[\s,]+(i\s+)?(do|consent|agree|accept|confirm|continue|proceed)|"
    r"(i\s+)?(consent|agree|accept)|"
    r"continue|proceed|go\s+ahead|let'?s\s+go)\b",
    re.I,
)

YES_RE = re.compile(
    r"^\s*(yes|yeah|yep|yup|y|ok|okay|sure|i\s+do|i\s+have|"
    r"yes[\s,]+(i\s+)?(do|have|did))\b",
    re.I,
)
NO_RE = re.compile(r"^\s*(no|n|nope|nah|not really|never)\b", re.I)

ConsentVerdict = Literal["yes", "no", "unclear"]


@dataclass(frozen=True)
class StepDef:
    id: str
    prompt: str
    field: str | None = None
    section: str = "intake"


@dataclass(frozen=True)
class RedFlagStep:
    id: str
    prompt: str
    field: str
    flag_type: str
    severity: Literal["emergency", "specialist"]
    reply: str
    requires_pain_context: bool = False


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

RED_FLAG_STEPS: list[RedFlagStep] = [
    RedFlagStep(
        "red_flag_bladder_bowel",
        "Have you had any loss of control of your bladder or bowel — even slightly — since this started?",
        "bladder_bowel",
        "cauda_equina",
        "emergency",
        "Please go to the nearest hospital immediately. This cannot wait.",
        requires_pain_context=True,
    ),
    RedFlagStep(
        "red_flag_unilateral_weakness",
        "Have you noticed any sudden weakness on one side of your body, or difficulty speaking or swallowing?",
        "unilateral_weakness_speech",
        "stroke",
        "emergency",
        "Please call emergency services or go to hospital now. Do not wait.",
    ),
    RedFlagStep(
        "red_flag_severe_headache",
        "Have you had a sudden, severe headache — the worst of your life?",
        "severe_headache",
        "subarachnoid",
        "emergency",
        "Please go to the nearest hospital or emergency room now. Do not wait.",
    ),
    RedFlagStep(
        "red_flag_weight_loss",
        "Have you noticed any unexplained weight loss recently — without trying?",
        "unexplained_weight_loss",
        "malignancy",
        "specialist",
        "Based on what you've shared, I want a specialist to review this carefully before we book routine care. I'll make sure you're routed appropriately.",
        requires_pain_context=True,
    ),
    RedFlagStep(
        "red_flag_fever",
        "Do you have a fever alongside this pain?",
        "fever",
        "infection",
        "specialist",
        "A fever with pain needs specialist review first. I'll make sure you're routed to the right care.",
    ),
    RedFlagStep(
        "red_flag_trauma",
        "Have you had a recent significant injury — a fall, accident, or impact?",
        "recent_trauma",
        "trauma",
        "specialist",
        "Got it — with a recent injury we need to be careful. Have you had any imaging (X-ray or scan) done for this?",
    ),
    RedFlagStep(
        "red_flag_joint_inflammation",
        "Is there any redness, swelling or warmth over the joint or area?",
        "joint_heat_swelling",
        "septic_arthritis",
        "specialist",
        "Redness, swelling or warmth can need urgent specialist review. I'll flag this for priority routing.",
    ),
    RedFlagStep(
        "red_flag_cancer",
        "Are you currently being treated for any form of cancer?",
        "cancer_history",
        "malignancy",
        "emergency",
        "Thank you for telling me. With cancer history, bone or joint pain needs specialist attention urgently — please seek care now and come back to me after.",
    ),
]

CULTURAL_STEPS: list[StepDef] = [
    StepDef(
        "cultural_self_treatment",
        "Before we go further — what have you already tried for this? For example rest, pain gel, balm, herbs, painkillers, or anything else?",
        "self_treatment_tried",
        "cultural",
    ),
    StepDef(
        "cultural_prior_specialist",
        "Have you seen a doctor or specialist about this before?",
        "seen_specialist_before",
        "cultural",
    ),
]

RED_FLAG_BY_ID = {s.id: s for s in RED_FLAG_STEPS}

STEP_BY_ID: dict[str, StepDef] = {
    s.id: s
    for s in CLINICAL_STEPS + PAIN_STEPS + NEURO_STEPS + FUNCTIONAL_STEPS + CULTURAL_STEPS
}

INTAKE_COMPLETE_STEP = "cultural_complete"
INITIAL_STEP = "start"
OLD_FLOW_STEPS = {
    "consent_pending",
    "profile_first_name",
    "profile_last_name",
    "profile_gender",
    "profile_dob",
    "profile_email",
    "profile_country",
    "profile_state",
    "profile_city",
    "profile_phone_confirm",
    "profile_consultation_preference",
    "complaint_complete",
}


def parse_consent(raw: str) -> ConsentVerdict:
    """Classify light-consent replies. Affirmative phrases like 'yes i consent' count as yes."""
    text = raw.strip()
    if not text:
        return "unclear"

    lowered = text.lower()

    # Clear refusal takes priority when message is short / refusal-led
    if CONSENT_NO_RE.search(lowered) and not CONSENT_YES_RE.search(lowered):
        return "no"
    if re.search(r"\b(don'?t|do not|won'?t)\s+(consent|agree|accept)\b", lowered):
        return "no"

    if CONSENT_YES_RE.search(lowered):
        return "yes"

    # Soft affirmatives that don't start the string
    if re.search(r"\b(i\s+consent|i\s+agree|yes\s+i\s+do|yes\s+i\s+consent)\b", lowered):
        return "yes"

    return "unclear"


def parse_yes_no(raw: str) -> ConsentVerdict:
    text = raw.strip()
    if not text:
        return "unclear"
    if YES_RE.search(text) and not CONSENT_NO_RE.search(text):
        return "yes"
    if NO_RE.search(text) and not CONSENT_YES_RE.search(text):
        return "no"
    # "a little", "slightly", "sometimes" treated as yes for red-flag safety
    if re.search(r"\b(a little|slightly|sometimes|once|kind of|sort of)\b", text, re.I):
        return "yes"
    return "unclear"


def default_intake_data() -> dict[str, Any]:
    return {
        "flow_version": FLOW_VERSION,
        "profile": {},
        "clinical_history": {},
        "complaint": {},
        "red_flags": {},
        "cultural": {},
        "pathways": [],
        "pathway_queue": [],
        "red_flag_triggered": False,
        "red_flag_type": None,
    }


def detect_pathways(text: str) -> list[str]:
    pathways: list[str] = []
    if PAIN_KEYWORDS.search(text):
        pathways.append("pain")
    if NEURO_KEYWORDS.search(text):
        pathways.append("neuro")
    return pathways


def _parse_severity(raw: str) -> tuple[int | None, str | None]:
    match = re.search(r"\b(10|[1-9])\b", raw.strip())
    if not match:
        return None, "Please give a number from 1 to 10."
    value = int(match.group(1))
    if 1 <= value <= 10:
        return value, None
    return None, "Please give a number from 1 to 10."


def _parse_name(raw: str) -> tuple[str | None, str | None]:
    text = raw.strip()
    # Strip common prefixes like "my name is", "call me", "i am"
    text = re.sub(
        r"^(my name is|i am|i'm|call me|it's|it is)\s+",
        "",
        text,
        flags=re.I,
    ).strip()
    text = text.strip(" .,!?'\"")
    if len(text) < 1:
        return None, "What can I call you?"
    if len(text) > 80:
        return None, "Please share a shorter name I can use."
    # Reject if it looks like a sentence about symptoms
    if PAIN_KEYWORDS.search(text) or NEURO_KEYWORDS.search(text):
        return None, "Thanks — first, what can I call you? Just your first name is fine."
    # Take first token group as name (allow multi-word first names)
    parts = text.split()
    name = " ".join(parts[:3]).title()
    return name, None


def validate_step(step_id: str, raw: str, intake_data: dict[str, Any], phone: str) -> tuple[Any, str | None]:
    text = raw.strip()
    if not text:
        return None, "I didn't catch that — could you try again?"

    if step_id == "ask_name":
        return _parse_name(text)

    if step_id in {"complaint_pain_severity_now", "complaint_pain_severity_worst"}:
        return _parse_severity(text)

    if step_id.startswith("red_flag_"):
        verdict = parse_yes_no(text)
        if verdict == "unclear":
            return None, "Please reply YES or NO so I can keep you safe."
        return verdict == "yes", None

    return text, None


def prompt_for_step(step_id: str, intake_data: dict[str, Any], phone: str, name: str | None = None) -> str:
    if step_id == "ask_name":
        return NAME_PROMPT
    if step_id == "light_consent":
        return LIGHT_CONSENT_TEMPLATE.format(name=name or "there")
    if step_id == "complaint_opening":
        return COMPLAINT_OPENING
    if step_id == "complaint_pathway_clarify":
        return PATHWAY_CLARIFY

    if step_id in RED_FLAG_BY_ID:
        return RED_FLAG_BY_ID[step_id].prompt

    step = STEP_BY_ID.get(step_id)
    if not step:
        return "Let's continue — could you answer my last question?"
    return step.prompt


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
    current_pathway = "pain" if steps is PAIN_STEPS else "neuro" if steps is NEURO_STEPS else None
    if queue and current_pathway and queue[0] == current_pathway:
        queue.pop(0)
        intake_data["pathway_queue"] = queue
    if queue:
        return _first_pathway_step(queue[0])
    return FUNCTIONAL_STEPS[0].id


def next_step_id(current: str, intake_data: dict[str, Any]) -> str:
    if current == "ask_name":
        return "light_consent"
    if current == "light_consent":
        return "complaint_opening"

    if current == "complaint_opening":
        pathways = intake_data.get("pathways") or []
        intake_data["pathway_queue"] = list(pathways)
        if not pathways:
            return "complaint_pathway_clarify"
        return _first_pathway_step(pathways[0])

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
        return RED_FLAG_STEPS[0].id

    for i, step in enumerate(RED_FLAG_STEPS):
        if step.id == current:
            return RED_FLAG_STEPS[i + 1].id if i + 1 < len(RED_FLAG_STEPS) else CLINICAL_STEPS[0].id

    for i, step in enumerate(CLINICAL_STEPS):
        if step.id == current:
            return CLINICAL_STEPS[i + 1].id if i + 1 < len(CLINICAL_STEPS) else CULTURAL_STEPS[0].id

    for i, step in enumerate(CULTURAL_STEPS):
        if step.id == current:
            return CULTURAL_STEPS[i + 1].id if i + 1 < len(CULTURAL_STEPS) else INTAKE_COMPLETE_STEP

    return INTAKE_COMPLETE_STEP


def is_intake_in_progress(step: str | None) -> bool:
    if not step:
        return True
    return step not in {INTAKE_COMPLETE_STEP, "complete", "red_flag_stopped"}


def section_for_step(step_id: str) -> str:
    if step_id in RED_FLAG_BY_ID:
        return "red_flags"
    if step_id in STEP_BY_ID:
        return STEP_BY_ID[step_id].section
    if step_id.startswith("clinical_"):
        return "clinical_history"
    if step_id.startswith("cultural_"):
        return "cultural"
    if step_id.startswith("complaint_"):
        return "complaint"
    if step_id in {"ask_name", "light_consent", "start"}:
        return "profile"
    return "complaint"


def complaint_suggests_back_or_neck(intake_data: dict[str, Any]) -> bool:
    complaint = intake_data.get("complaint") or {}
    blob = " ".join(str(v) for v in complaint.values()).lower()
    return bool(re.search(r"\b(back|neck|spine|lumbar|cervical)\b", blob))


def evaluate_red_flag_answer(
    step_id: str,
    answered_yes: bool,
    intake_data: dict[str, Any],
) -> tuple[bool, str | None, str | None]:
    """Return (triggered, reply, flag_type)."""
    step = RED_FLAG_BY_ID.get(step_id)
    if not step or not answered_yes:
        return False, None, None

    if step.requires_pain_context and step.flag_type == "cauda_equina":
        if not complaint_suggests_back_or_neck(intake_data):
            # Still note the answer but don't fire cauda equina without back/neck context
            return False, None, None

    if step.flag_type == "septic_arthritis":
        fever = (intake_data.get("red_flags") or {}).get("fever")
        if fever is not True:
            # Flag alone without fever → still specialist note, milder
            return True, step.reply, step.flag_type

    return True, step.reply, step.flag_type
