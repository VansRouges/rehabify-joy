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
        "intake_session_id": None,
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
    assert "quietly" in compiled.system.lower()
    assert "noted" in compiled.system.lower()


def test_compiler_keeps_new_threads_from_resuming_intake():
    patient = _patient(
        known_facts={"name": "Tunde", "complaint": "back pain"},
        intake_step="complaint_functional_limitations",
        conversation_summary="Lower back pain from sitting",
    )
    compiled = compile_context(
        patient,
        [],
        max_turns=12,
        base_prompt="You are Joy.",
        intake_open_elsewhere=True,
        new_thread=True,
    )
    text = compiled.system.lower()
    assert "check in with care" in text
    assert "another thread" in text
    assert "do not continue a questionnaire" in text
    assert "tunde" in text
    assert "back pain" in text


def test_joy_prompt_is_feminine_and_does_not_narrate_notes():
    from pathlib import Path

    prompt = (Path(__file__).resolve().parents[1] / "app" / "prompts" / "joy_system_prompt.txt").read_text(
        encoding="utf-8"
    )
    assert "Joy is a woman" in prompt
    assert "I've noted" not in prompt
    assert "not in every message" in prompt


def test_intake_replies_do_not_say_noted_that():
    import inspect

    from app.services import flow_engine

    source = inspect.getsource(flow_engine)
    assert "I've noted" not in source
    assert "acknowledge(" not in source


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


def test_new_web_thread_does_not_steal_intake():
    from app.services.flow_engine import patient_needs_intake, session_owns_intake

    patient = _patient(
        known_facts={"name": "Tunde", "complaint": "back pain"},
        consent_given=True,
        intake_step="complaint_functional_limitations",
        intake_data={"flow_version": 2, "complaint": {"presenting_complaint": "back pain"}},
    )
    assert patient_needs_intake(patient) is True

    first = "11111111-1111-1111-1111-111111111111"
    second = "22222222-2222-2222-2222-222222222222"
    run, owner = session_owns_intake(
        needs_intake=True,
        intake_session_id=None,
        current_session_id=second,
        earliest_session_id=first,
        channel="web",
    )
    assert run is False
    assert owner == first

    run_same, owner_same = session_owns_intake(
        needs_intake=True,
        intake_session_id=first,
        current_session_id=first,
        earliest_session_id=first,
        channel="web",
    )
    assert run_same is True
    assert owner_same == first


def test_whatsapp_keeps_intake_on_active_session():
    from app.services.flow_engine import session_owns_intake

    current = "33333333-3333-3333-3333-333333333333"
    run, owner = session_owns_intake(
        needs_intake=True,
        intake_session_id="11111111-1111-1111-1111-111111111111",
        current_session_id=current,
        earliest_session_id="11111111-1111-1111-1111-111111111111",
        channel="whatsapp",
    )
    assert run is True
    assert owner == current


def test_first_web_session_owns_intake():
    from app.services.flow_engine import session_owns_intake

    current = "44444444-4444-4444-4444-444444444444"
    run, owner = session_owns_intake(
        needs_intake=True,
        intake_session_id=None,
        current_session_id=current,
        earliest_session_id=None,
        channel="web",
    )
    assert run is True
    assert owner == current


def test_check_in_names_the_ailment_and_offers_a_choice():
    from app.services.thread_opening import ailment_phrase, build_check_in, classify_thread_choice

    patient = _patient(
        display_name="Tunde",
        known_facts={"name": "Tunde", "complaint": "My lower back has been aching"},
        intake_data={"complaint": {"presenting_complaint": "My lower back has been aching"}},
    )
    text = build_check_in(patient)
    assert "Hey Tunde" in text
    assert "your lower back" in text
    assert "better" in text
    assert "pick up where we left off" in text
    assert "something new" in text
    assert ailment_phrase("pain in my left knee") == "your knee"
    assert classify_thread_choice("hey joy, remember me?") == "greeting"
    assert classify_thread_choice("hey joy") == "greeting"
    assert classify_thread_choice("pick up where we left off") == "pick_up"
    assert classify_thread_choice("let's talk about something new") == "new_topic"
    assert classify_thread_choice("no") == "not_better"


def test_alembic_keeps_versioned_migrations():
    from alembic.config import Config
    from alembic.script import ScriptDirectory

    from app.db.database import ALEMBIC_INI

    script = ScriptDirectory.from_config(Config(str(ALEMBIC_INI)))
    revisions = list(script.walk_revisions())
    ids = {rev.revision for rev in revisions}
    assert "0001_baseline" in ids
    assert script.get_current_head() == "0001_baseline"
