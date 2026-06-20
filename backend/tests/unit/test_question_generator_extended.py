from __future__ import annotations

import json
from unittest.mock import MagicMock
import pytest
from backend.services.questions.generator import QuestionGenerator, _interpolate


# ---------- _interpolate ----------

def test_interpolate_replaces_known_variable():
    result = _interpolate("You are applying for {{position}} at {{company}}.", {
        "position": "SWE", "company": "Acme"
    })
    assert result == "You are applying for SWE at Acme."


def test_interpolate_leaves_unknown_variable():
    result = _interpolate("Tell me about {{tech_stack}}.", {})
    assert "{{tech_stack}}" in result


def test_interpolate_empty_template():
    assert _interpolate("", {"company": "X"}) == ""


# ---------- QuestionGenerator fixtures ----------

@pytest.fixture
def mock_ollama_off():
    o = MagicMock()
    o.is_available.return_value = False
    return o


@pytest.fixture
def mock_ollama_on():
    o = MagicMock()
    o.is_available.return_value = True
    o.generate.return_value = json.dumps([
        {"question_template": "Why do you want to work at {{company}}?", "category": "motivational"},
        {"question_template": "Describe a time you used {{tech_stack}}.", "category": "technical"},
    ])
    return o


@pytest.fixture
def mock_loader():
    loader = MagicMock()
    loader.load.return_value = {
        "system": "Generate questions",
        "user_template": (
            "JD: {job_description}\nCompany: {company}\nPosition: {position}\n"
            "Industry: {industry}\nTech: {tech_stack}"
        ),
    }
    return loader


@pytest.fixture
def mock_selector():
    sel = MagicMock()
    sel.select.return_value = [
        {"bullet_text": "Led Python work", "evidence_id": "b1", "experience_id": "e1",
         "company": "Acme", "title": "SWE", "dates": "2022–2024", "confidence": "verified"}
    ]
    return sel


# ---------- generate_questions ----------

def test_generate_questions_no_ollama_uses_fallback(mock_ollama_off, mock_loader, mock_selector, test_session):
    gen = QuestionGenerator(mock_ollama_off, mock_loader, mock_selector, test_session)
    results = gen.generate_questions("Python engineer at Acme", company="Acme", position="SWE")
    assert len(results) > 0
    assert all("question_template" in q for q in results)
    assert all("interpolated" in q for q in results)


def test_generate_questions_fallback_interpolates_variables(mock_ollama_off, mock_loader, mock_selector, test_session):
    gen = QuestionGenerator(mock_ollama_off, mock_loader, mock_selector, test_session)
    results = gen.generate_questions("role", company="Google", position="PM", industry="tech", tech_stack="Python")
    # Fallback template includes {{company}} — should be replaced
    interpolated_texts = [q["interpolated"] for q in results]
    assert any("Google" in t or "PM" in t or "tech" in t for t in interpolated_texts)


def test_generate_questions_with_ollama_returns_llm_questions(mock_ollama_on, mock_loader, mock_selector, test_session):
    gen = QuestionGenerator(mock_ollama_on, mock_loader, mock_selector, test_session)
    results = gen.generate_questions("Python engineer at Acme", company="Acme", position="SWE", tech_stack="Python")
    assert len(results) == 2
    assert results[0]["category"] == "motivational"


def test_generate_questions_invalid_category_defaults_to_behavioral(mock_loader, mock_selector, test_session):
    o = MagicMock()
    o.is_available.return_value = True
    o.generate.return_value = json.dumps([
        {"question_template": "Ask about {{position}}?", "category": "nonexistent_category"}
    ])
    gen = QuestionGenerator(o, mock_loader, mock_selector, test_session)
    results = gen.generate_questions("role", position="Dev")
    assert results[0]["category"] == "behavioral"


def test_generate_questions_llm_json_error_uses_fallback(mock_loader, mock_selector, test_session):
    o = MagicMock()
    o.is_available.return_value = True
    o.generate.return_value = "not json at all"
    gen = QuestionGenerator(o, mock_loader, mock_selector, test_session)
    results = gen.generate_questions("Python role")
    assert len(results) > 0  # fallback was used


# ---------- generate_answer ----------

def test_generate_answer_invalid_length_raises(mock_ollama_off, mock_loader, mock_selector, test_session):
    gen = QuestionGenerator(mock_ollama_off, mock_loader, mock_selector, test_session)
    with pytest.raises(ValueError, match="Invalid length_target"):
        gen.generate_answer("some-question-id", {}, length_target="epic")


def test_generate_answer_question_not_found_raises(mock_ollama_off, mock_loader, mock_selector, test_session):
    gen = QuestionGenerator(mock_ollama_off, mock_loader, mock_selector, test_session)
    with pytest.raises(ValueError, match="Question not found"):
        gen.generate_answer("non-existent-uuid-1234", {}, length_target="short")


def test_generate_answer_success(mock_ollama_on, mock_loader, mock_selector, test_session):
    # First create a question
    gen = QuestionGenerator(mock_ollama_on, mock_loader, mock_selector, test_session)
    questions = gen.generate_questions("Python role", company="Acme", position="SWE", tech_stack="Python")
    assert len(questions) > 0
    q_id = questions[0]["id"]

    # Now configure ollama to return an answer
    mock_ollama_on.generate.return_value = "I demonstrated leadership by mentoring 3 engineers..."
    answer = gen.generate_answer(q_id, {"company": "Acme", "position": "SWE", "tech_stack": "Python"}, length_target="medium")
    assert "answer_id" in answer
    assert answer["question_id"] == q_id
    assert "interpolated_question" in answer


# ---------- edit_answer ----------

def test_edit_answer_not_found_raises(mock_ollama_on, mock_loader, mock_selector, test_session):
    gen = QuestionGenerator(mock_ollama_on, mock_loader, mock_selector, test_session)
    with pytest.raises(ValueError, match="Answer not found"):
        gen.edit_answer("fake-answer-uuid", "my edited text")
