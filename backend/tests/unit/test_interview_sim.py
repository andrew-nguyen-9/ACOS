"""15.3 — recruiter persona + answer follow-ups (interview simulation deepening)."""
from __future__ import annotations

from unittest.mock import MagicMock

from backend.services.questions.generator import QuestionGenerator, _FALLBACK_FOLLOWUPS


def _gen(session, ollama):
    loader = MagicMock()
    selector = MagicMock()
    selector.select.return_value = []
    return QuestionGenerator(ollama, loader, selector, session), loader


def test_persona_threads_into_question_system_prompt(test_session):
    ollama = MagicMock()
    ollama.is_available.return_value = True
    ollama.generate.return_value = '[{"question_template": "Q {{company}}", "category": "behavioral"}]'
    gen, loader = _gen(test_session, ollama)
    loader.load.return_value = {
        "system": "SYS",
        "user_template": "{job_description}{company}{position}{industry}{tech_stack}",
    }

    gen.generate_questions("jd text", company="Acme", persona="skeptical")

    system = ollama.generate.call_args.kwargs["system"]
    assert "skeptical" in system.lower()


def test_followups_use_llm_and_persona(test_session):
    ollama = MagicMock()
    ollama.is_available.return_value = True
    ollama.generate.return_value = '["Can you quantify that?", "What was the trade-off?"]'
    gen, loader = _gen(test_session, ollama)
    loader.load.return_value = {"system": "SYS", "user_template": "{question}{answer}{max_followups}"}

    res = gen.generate_followups("Tell me about X", "I led the migration.", persona="technical")

    assert res == ["Can you quantify that?", "What was the trade-off?"]
    assert "technical" in ollama.generate.call_args.kwargs["system"].lower()


def test_followups_fallback_when_ollama_down(test_session):
    ollama = MagicMock()
    ollama.is_available.return_value = False
    gen, _ = _gen(test_session, ollama)
    res = gen.generate_followups("Q", "some answer", max_followups=2)
    assert res == _FALLBACK_FOLLOWUPS[:2]


def test_followups_empty_answer_returns_nothing(test_session):
    ollama = MagicMock()
    ollama.is_available.return_value = False
    gen, _ = _gen(test_session, ollama)
    assert gen.generate_followups("Q", "   ") == []
