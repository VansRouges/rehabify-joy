from __future__ import annotations

import re
from dataclasses import dataclass

LanguageCode = str  # en | pcm | yo | ig | ha

_PIDGIN = re.compile(
    r"\b(wetin|dey|abeg|wahala|una|fit|no be|how you dey|i dey|make i|na so|chai)\b",
    re.I,
)
_YORUBA = re.compile(
    r"\b(pele|bawo|e se|e ku|nse|se daadaa|mo dupe|eki|aburo|egbon)\b|[ẹọṣ]",
    re.I,
)
_IGBO = re.compile(
    r"\b(ndewo|kedu|biko|daalu|nno|kedu ka|imela|nwanne)\b",
    re.I,
)
_HAUSA = re.compile(
    r"\b(sannu|na gode|yaya|lahiya|ina kwana|madalla|kai|gaskiya)\b",
    re.I,
)


@dataclass
class LanguageGuess:
    code: LanguageCode
    confidence: str  # "high" | "low"


def detect_language(text: str, fallback: str | None = None) -> LanguageGuess:
    sample = (text or "").strip()
    if not sample:
        return LanguageGuess(code=fallback or "en", confidence="low")

    scores: dict[str, int] = {"pcm": 0, "yo": 0, "ig": 0, "ha": 0}
    if _PIDGIN.search(sample):
        scores["pcm"] += 2
    if _YORUBA.search(sample):
        scores["yo"] += 2
    if _IGBO.search(sample):
        scores["ig"] += 2
    if _HAUSA.search(sample):
        scores["ha"] += 2

    best = max(scores, key=lambda k: scores[k])
    if scores[best] == 0:
        if fallback:
            return LanguageGuess(code=fallback, confidence="low")
        return LanguageGuess(code="en", confidence="low")
    return LanguageGuess(code=best, confidence="high" if scores[best] >= 2 else "low")
