from __future__ import annotations

import pytest
from unittest.mock import MagicMock

from backend.services.questions.generator import QuestionGenerator, _interpolate


def _make_generator(session, ollama=None, loader=None, selector=None):
    if ollama is None:
        ollama = MagicMock()
        ollama.is_available.return_value = False
    if loader is None:
        loader = MagicMock()
    if selector is None:
        selector = MagicMock()
        selector.select.return_value = []
    return QuestionGenerator(ollama, loader, selector, session)


def test_interpolate_replaces_variables():
    result = _interpolate("Tell me about {{company}} as a {{position}}.", {"company": "Acme", "position": "Engineer"})
    assert result == "Tell me about Acme as a Engineer."


def test_interpolate_leaves_unknown_variables():
    result = _interpolate("What is {{unknown}}?", {})
    assert result == "What is {{unknown}}?"


def test_interpolate_empty_template():
    assert _interpolate("", {"company": "A"}) == ""


def test_generate_questions_fallback_when_ollama_unavailable(test_session):
    gen = _make_generator(test_session)
    results = gen.generate_questions(
        "Python developer role at Acme", company="Acme", position="Dev"
    )
    assert isinstance(results, list)
    assert len(results) > 0
    for q in results:
        assert "id" in q
        assert "question_template" in q
        assert "interpolated" in q
        assert "category" in q
        assert "variables" in q


def test_generate_questions_stores_in_db(test_session):
    gen = _make_generator(test_session)
    results = gen.generate_questions("Role description", company="Foo", position="Bar")
    from backend.repositories.question import QuestionRepository
    repo = QuestionRepository(test_session)
    assert repo.count() == len(results)


def test_generate_questions_interpolates_variables(test_session):
    gen = _make_generator(test_session)
    results = gen.generate_questions(
        "Dev role", company="Acme", position="Engineer", industry="Tech"
    )
    for q in results:
        assert "{{company}}" not in q["interpolated"]
        assert "{{position}}" not in q["interpolated"]


def test_generate_answer_invalid_length(test_session):
    gen = _make_generator(test_session)
    with pytest.raises(ValueError, match="Invalid length_target"):
        gen.generate_answer("any-id", {}, length_target="xl")


def test_generate_answer_question_not_found(test_session):
    gen = _make_generator(test_session)
    with pytest.raises(ValueError, match="Question not found"):
        gen.generate_answer("doesnotexist", {})


def test_generate_answer_stores_in_db(test_session):
    gen = _make_generator(test_session)
    questions = gen.generate_questions("Dev role", company="Acme", position="Dev")
    q_id = questions[0]["id"]
    result = gen.generate_answer(q_id, {"company": "Acme", "position": "Dev"})
    assert "answer_id" in result
    assert "original_answer" in result
    assert result["confidence_level"] in ("verified", "strong_inference", "weak_inference")
    assert isinstance(result["requires_approval"], bool)


def test_generate_answer_requires_approval_for_weak_inference(test_session):
    selector = MagicMock()
    selector.select.return_value = []  # no evidence → weak_inference
    gen = _make_generator(test_session, selector=selector)
    questions = gen.generate_questions("Dev role")
    q_id = questions[0]["id"]
    result = gen.generate_answer(q_id, {})
    assert result["requires_approval"] is True
    assert result["confidence_level"] == "weak_inference"


def test_edit_answer(test_session):
    gen = _make_generator(test_session)
    questions = gen.generate_questions("Dev role")
    q_id = questions[0]["id"]
    answer_result = gen.generate_answer(q_id, {})
    answer_id = answer_result["answer_id"]
    edited = gen.edit_answer(answer_id, "My edited answer", diff_summary="Changed tone")
    assert edited["edited_answer"] == "My edited answer"
    assert edited["diff_summary"] == "Changed tone"
    assert "original_answer" in edited


def test_edit_answer_not_found(test_session):
    gen = _make_generator(test_session)
    with pytest.raises(ValueError, match="Answer not found"):
        gen.edit_answer("doesnotexist", "text")
