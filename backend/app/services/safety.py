import re
from dataclasses import dataclass

RED_FLAG_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("chest_pain", re.compile(r"\bchest pain\b", re.I)),
    ("difficulty_breathing", re.compile(r"\b(can'?t breathe|difficulty breathing|shortness of breath|can'?t catch my breath)\b", re.I)),
    ("stroke_symptoms", re.compile(r"\b(one.?sided weakness|sudden weakness|face droop|slurred speech|difficulty speaking|can'?t speak properly)\b", re.I)),
    ("severe_headache", re.compile(r"\b(sudden severe headache|worst headache|thunderclap headache)\b", re.I)),
    ("loss_of_consciousness", re.compile(r"\b(passed out|lost consciousness|fainted|blacked out)\b", re.I)),
    ("bladder_bowel", re.compile(r"\b(loss of bladder|loss of bowel|can'?t control bladder|can'?t control bowel|incontinence)\b", re.I)),
    ("suspected_fracture", re.compile(r"\b(broken bone|suspected fracture|bone sticking out|deformed limb)\b", re.I)),
    ("recent_trauma", re.compile(r"\b(car accident|fell from|major trauma|hit by)\b", re.I)),
]

EMERGENCY_REPLY = (
    "Based on what you've shared, this needs urgent medical attention right now — "
    "please call 112 or go to the nearest emergency department immediately. "
    "Your safety comes first. Once you've been seen by a doctor, come back to me "
    "and we'll take care of your physiotherapy from there."
)

OFF_TOPIC_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"\b(write (me )?a (code|script|essay|poem|story))\b", re.I),
    re.compile(r"\b(stock market|crypto|bitcoin|politics|election)\b", re.I),
    re.compile(r"\b(recipe|cook|movie|song lyrics|homework)\b", re.I),
]

OFF_TOPIC_REPLY = (
    "I'm Joy from Rehabify — I help with physiotherapy and recovery. "
    "Tell me what's been bothering your body, and we'll figure out the best next step together."
)


@dataclass
class SafetyResult:
    blocked: bool
    reply: str | None = None
    flag_type: str | None = None


def check_red_flags(message: str) -> SafetyResult:
    for flag_type, pattern in RED_FLAG_PATTERNS:
        if pattern.search(message):
            return SafetyResult(blocked=True, reply=EMERGENCY_REPLY, flag_type=flag_type)
    return SafetyResult(blocked=False)


def check_off_topic(message: str) -> SafetyResult:
    for pattern in OFF_TOPIC_PATTERNS:
        if pattern.search(message):
            return SafetyResult(blocked=True, reply=OFF_TOPIC_REPLY, flag_type="off_topic")
    return SafetyResult(blocked=False)
