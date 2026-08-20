from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

from app.db.models import AuditEvent, Patient
from app.language.detect import detect_language
from app.llm.gemini import _parse_protocol
from app.llm.router import get_llm_client
from app.memory.compiler import compile_context
from app.memory.facts import remember_fact
from app.services.safety import check_red_flags


def _patient(**kwargs) -> Patient:
    defaults = {
        "display_name": "Ada",
        "phone_number": "+2348011111111",
        "consent_given": True,
        "intake_data": {},
        "known_facts": {},
        "language_preference": "en",
        "conversation_summary": None,
        "persona": "patient",
        "region": None,
        "intake_step": "cultural_complete",
    }
    defaults.update(kwargs)
    return Patient(**defaults)


def test_patient_model_has_memory_columns():
    assert hasattr(Patient, "language_preference")
    assert hasattr(Patient, "known_facts")
    assert hasattr(Patient, "conversation_summary")
    assert hasattr(Patient, "persona")
    assert AuditEvent.__tablename__ == "audit_events"


def test_remember_fact_updates_known_facts_and_name():
    patient = _patient()
    remember_fact(patient, "name", "Tunde")
    remember_fact(patient, "complaint", "left knee pain")
    remember_fact(patient, "favourite_team", "Enyimba")
    assert patient.known_facts["name"] == "Tunde"
    assert patient.display_name == "Tunde"
    assert patient.known_facts["complaint"] == "left knee pain"
    assert patient.known_facts["custom"]["favourite_team"] == "Enyimba"


def test_compiler_omits_need_to_reask_known_name_and_complaint():
    patient = _patient(
        known_facts={"name": "Tunde", "complaint": "back pain", "intake_complete": True},
        conversation_summary="Last time: back pain, intake done",
    )
    compiled = compile_context(
        patient,
        [{"role": "user", "content": "I am back"}],
        max_turns=12,
        base_prompt="You are Joy.",
    )
    assert "do not re-ask" in compiled.system.lower()
    assert "Tunde" in compiled.system
    assert "back pain" in compiled.system
    assert "Last time:" in compiled.system
    assert "name" in compiled.known_keys
    assert "complaint" in compiled.known_keys


def test_language_fixtures():
    cases = json.loads(
        (Path(__file__).parent / "fixtures" / "language_cases.json").read_text(encoding="utf-8")
    )["cases"]
    for case in cases:
        guess = detect_language(case["text"])
        assert guess.code == case["expect"], (case["text"], guess.code, case["expect"])


def test_safety_english_and_pidgin_chest_pain():
    english = check_red_flags("I have severe chest pain right now", language="en")
    assert english.blocked
    assert english.flag_type == "chest_pain"
    assert "112" in (english.reply or "")

    pidgin = check_red_flags("Abeg my chest dey pain me bad", language="pcm")
    assert pidgin.blocked
    assert "112" in (pidgin.reply or "")
    assert "hospital" in (pidgin.reply or "").lower() or "abeg" in (pidgin.reply or "").lower()


def test_safety_yoruba_pattern():
    result = check_red_flags("chest dey pain", language="yo")
    assert result.blocked


def test_router_returns_gemini_for_default_brain(monkeypatch):
    monkeypatch.setattr(
        "app.llm.router.get_settings",
        lambda: SimpleNamespace(joy_default_brain="gemini", joy_language_polish="off"),
    )
    client = get_llm_client("gemini")
    from app.llm.gemini import GeminiClient

    assert isinstance(client, GeminiClient)


def test_parse_remember_fact_protocol():
    result = _parse_protocol('{"action":"remember_fact","key":"city","value":"Kano"}')
    assert result.tool_calls
    assert result.tool_calls[0].name == "remember_fact"
    assert result.tool_calls[0].arguments == {"key": "city", "value": "Kano"}


def test_parse_reply_protocol():
    result = _parse_protocol('{"action":"reply","text":"Pele, tell me more."}')
    assert result.text == "Pele, tell me more."
    assert result.tool_calls == []


def test_should_run_intake_skips_when_facts_complete():
    from app.services.flow_engine import should_run_intake

    patient = _patient(known_facts={"intake_complete": True}, consent_given=True)
    assert should_run_intake(patient) is False
