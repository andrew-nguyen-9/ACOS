"""Phase 12.8 Spike A — structured output (Ollama ``format`` = JSON Schema).

The JSON-extraction routes pass a JSON Schema to ``generate(output_format=...)``
when ``ACOS_ENABLE_STRUCTURED_OUTPUT`` is on, pairing it with ``think=False``
(qwen3 reasoning blocks would break the schema constraint). Flag off → default
path unchanged (no ``output_format``, no forced ``think``).
"""
from __future__ import annotations

import json
from types import SimpleNamespace
from unittest.mock import MagicMock


def _flag(enabled: bool):
    return lambda: SimpleNamespace(enable_structured_output=enabled)


# ── entity_extractor ─────────────────────────────────────────────────────────

def test_entity_extractor_passes_schema_when_flag_on(monkeypatch):
    from backend.ingestion import entity_extractor as mod

    monkeypatch.setattr(mod, "get_settings", _flag(True))
    ollama = MagicMock()
    ollama.generate.return_value = json.dumps(
        {"skills": [], "experiences": [], "projects": []}
    )
    mod.EntityExtractor(ollama).extract("text", "resume")

    kwargs = ollama.generate.call_args.kwargs
    assert kwargs["output_format"] == mod._EXTRACT_SCHEMA
    assert kwargs["think"] is False


def test_entity_extractor_no_schema_when_flag_off(monkeypatch):
    from backend.ingestion import entity_extractor as mod

    monkeypatch.setattr(mod, "get_settings", _flag(False))
    ollama = MagicMock()
    ollama.generate.return_value = json.dumps(
        {"skills": [], "experiences": [], "projects": []}
    )
    mod.EntityExtractor(ollama).extract("text", "resume")

    kwargs = ollama.generate.call_args.kwargs
    assert kwargs.get("output_format") is None
    assert kwargs.get("think") is None


# ── ats scorer ───────────────────────────────────────────────────────────────

def test_ats_scorer_passes_schema_when_flag_on(monkeypatch):
    from backend.services.ats import scorer as mod

    monkeypatch.setattr(mod, "get_settings", _flag(True))
    ollama = MagicMock()
    ollama.is_available.return_value = True
    ollama.generate.return_value = json.dumps({"overall_score": 50})
    loader = MagicMock()
    loader.load.return_value = {"system": "s", "user_template": "{job_description}{resume_text}"}

    mod.ATSScorer(ollama, loader).score("resume", "jd", {})

    kwargs = ollama.generate.call_args.kwargs
    assert kwargs["output_format"] == mod._ATS_SCHEMA
    assert kwargs["think"] is False


# ── question generator ───────────────────────────────────────────────────────

def test_question_gen_passes_array_schema_when_flag_on(monkeypatch, test_session):
    from backend.services.questions import generator as mod

    monkeypatch.setattr(mod, "get_settings", _flag(True))
    ollama = MagicMock()
    ollama.is_available.return_value = True
    ollama.generate.return_value = json.dumps(
        [{"question_template": "Tell me about {{position}}", "category": "behavioral"}]
    )
    loader = MagicMock()
    loader.load.return_value = {"system": "s", "user_template": "{job_description}{company}{position}{industry}{tech_stack}"}
    gen = mod.QuestionGenerator(ollama, loader, MagicMock(), test_session)

    gen.generate_questions("jd", position="Dev")

    kwargs = ollama.generate.call_args.kwargs
    assert kwargs["output_format"] == mod._QUESTIONS_SCHEMA
    assert kwargs["think"] is False


def test_question_answer_passes_schema_when_flag_on(monkeypatch, test_session):
    from backend.services.questions import generator as mod

    monkeypatch.setattr(mod, "get_settings", _flag(True))
    ollama = MagicMock()
    ollama.is_available.return_value = True
    ollama.generate.return_value = json.dumps(
        {"answer_text": "I led X.", "confidence_level": "strong_inference"}
    )
    loader = MagicMock()
    loader.load.return_value = {"system": "s", "user_template": "{question}{evidence}{length_target}"}
    selector = MagicMock()
    selector.select.return_value = [
        {"evidence_id": "e1", "bullet_text": "Led X", "confidence": "strong_inference"}
    ]
    gen = mod.QuestionGenerator(ollama, loader, selector, test_session)

    q = mod.QuestionRepository(test_session).create(
        question_template="Tell me about {{position}}",
        category="behavioral",
        length_target="medium",
        variables=["position"],
        source="generated",
    )
    gen.generate_answer(q.id, {"position": "Dev"})

    kwargs = ollama.generate.call_args.kwargs
    assert kwargs["output_format"] == mod._ANSWER_SCHEMA
    assert kwargs["think"] is False
