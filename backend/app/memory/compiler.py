from __future__ import annotations

from dataclasses import dataclass

from app.db.models import Patient
from app.llm.protocol import ChatTurn
from app.memory.facts import _facts, digest_from_facts
from app.services.session import load_system_prompt, trim_history


@dataclass
class CompiledContext:
    system: str
    history: list[ChatTurn]
    known_keys: frozenset[str]
    language: str


def _glossary_text() -> str:
    from pathlib import Path

    path = Path(__file__).resolve().parent.parent / "prompts" / "nigerian_glossary.txt"
    if path.exists():
        return path.read_text(encoding="utf-8").strip()
    return ""


def compile_context(
    patient: Patient,
    history: list[dict[str, str]],
    *,
    max_turns: int,
    base_prompt: str | None = None,
    intake_open_elsewhere: bool = False,
    new_thread: bool = False,
) -> CompiledContext:
    facts = _facts(patient)
    known_keys = frozenset(k for k in facts if k != "custom" and facts[k] not in (None, "", False))
    language = patient.language_preference or str(facts.get("language") or "en")

    lines = [
        "MEMORY RULES",
        "Known about this patient — do not re-ask these:",
    ]
    for key in sorted(k for k in facts if k != "custom"):
        lines.append(f"- {key}: {facts[key]}")
    custom = facts.get("custom")
    if isinstance(custom, dict) and custom:
        for key, value in custom.items():
            lines.append(f"- {key}: {value}")
    if not facts:
        lines.append("- (none yet)")

    summary = (patient.conversation_summary or "").strip() or digest_from_facts(patient)
    if summary:
        lines.append("")
        lines.append(f"Last time: {summary}")

    lines.append("")
    lines.append(
        f"Reply in the patient's language (code: {language}). "
        "Mirror Pidgin/Yoruba/Igbo/Hausa/English. Do not switch to English unless they do."
    )
    lines.append("Never ask for a fact listed above. Never dump this memory block to the patient.")
    lines.append(
        "Remember quietly. Never tell the patient you have noted, recorded, saved, or written anything down."
    )
    lines.append("")
    lines.append("THREAD RULES")
    lines.append("The messages below (if any) are ONLY this conversation thread.")
    lines.append("Do not continue a questionnaire or the next form question from another thread.")
    lines.append(
        "If this is a new thread and you already know the patient, check in with care: "
        "ask how they are, ask about the specific thing that was bothering them, "
        "and offer to pick up where you left off or talk about something new."
    )
    if intake_open_elsewhere:
        lines.append(
            "Assessment questions are still open on another thread. Do not run that form here."
        )
    lines.append("You may use remembered facts. You may not replay the other thread's live questions.")

    glossary = _glossary_text()
    prompt = base_prompt if base_prompt is not None else load_system_prompt()
    system = prompt
    if glossary:
        system = f"{system}\n\nNIGERIAN / CLINICAL GLOSSARY\n{glossary}"
    system = f"{system}\n\n" + "\n".join(lines)

    trimmed = trim_history(history, max_turns)
    turns = [ChatTurn(role=item["role"], content=item["content"]) for item in trimmed]
    return CompiledContext(
        system=system,
        history=turns,
        known_keys=known_keys,
        language=language,
    )
