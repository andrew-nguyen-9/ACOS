from __future__ import annotations

import json
from unittest.mock import MagicMock
import pytest
from backend.services.cover_letter.generator import CoverLetterGenerator


@pytest.fixture
def mock_selector():
    sel = MagicMock()
    sel.select.return_value = [
        {"bullet_text": "Led Python migration saving $200K annually", "evidence_id": "b1",
         "experience_id": "e1", "company": "Acme", "title": "SWE",
         "dates": "2022–2024", "confidence": "verified"},
        {"bullet_text": "Possibly managed a team of 5", "evidence_id": "b2",
         "experience_id": "e1", "company": "Acme", "title": "SWE",
         "dates": "2022–2024", "confidence": "weak_inference"},
    ]
    return sel


@pytest.fixture
def mock_voice():
    vm = MagicMock()
    vm.get_or_create_default.return_value = {
        "tone_descriptors": ["professional", "confident"],
        "structure_patterns": ["hook → evidence → close"],
        "vocabulary_patterns": {},
        "sample_sentences": ["I am excited to apply."],
    }
    return vm


@pytest.fixture
def mock_loader():
    loader = MagicMock()
    loader.load.return_value = {
        "system": "Write cover letter",
        "user_template": (
            "JD: {job_description}\nCompany: {company}\nTitle: {job_title}\n"
            "Length: {length_target}\nTone: {tone_descriptors}\n"
            "Vocab: {vocabulary_patterns}\nSamples: {sample_sentences}\n"
            "Industry: {industry}\nKeywords: {keywords}\nEvidence: {evidence_json}"
        ),
    }
    return loader


def test_generate_template_path_no_ollama(mock_selector, mock_voice, mock_loader):
    ollama = MagicMock()
    ollama.is_available.return_value = False
    gen = CoverLetterGenerator(mock_selector, mock_voice, ollama, mock_loader)
    result = gen.generate("Python engineer role", "Acme", "SWE", "medium")
    assert "text" in result
    assert isinstance(result["text"], str)
    assert len(result["text"]) > 0


def test_generate_weak_evidence_sets_requires_approval(mock_voice, mock_loader):
    sel = MagicMock()
    sel.select.return_value = [
        {"bullet_text": "Possibly led team", "evidence_id": "b1", "experience_id": "e1",
         "company": "Co", "title": "Lead", "dates": "2020–2022", "confidence": "weak_inference"}
    ]
    ollama = MagicMock()
    ollama.is_available.return_value = False
    gen = CoverLetterGenerator(sel, mock_voice, ollama, mock_loader)
    result = gen.generate("Management role", "Corp", "Manager", "short")
    assert result["requires_approval"] is True


def test_generate_invalid_length_raises(mock_selector, mock_voice, mock_loader):
    ollama = MagicMock()
    ollama.is_available.return_value = False
    gen = CoverLetterGenerator(mock_selector, mock_voice, ollama, mock_loader)
    with pytest.raises(ValueError, match="Invalid length_target"):
        gen.generate("anything", "Co", "Dev", "enormous")


def test_generate_llm_success(mock_selector, mock_voice, mock_loader):
    ollama = MagicMock()
    ollama.is_available.return_value = True
    ollama.generate.return_value = "Dear Hiring Manager, I am the right candidate."
    gen = CoverLetterGenerator(mock_selector, mock_voice, ollama, mock_loader)
    result = gen.generate("Python engineer role", "Acme", "SWE", "medium")
    assert result["text"] == "Dear Hiring Manager, I am the right candidate."
    assert result["requires_approval"] is True  # because weak_inference in evidence


def test_generate_llm_exception_falls_back_to_template(mock_selector, mock_voice, mock_loader):
    ollama = MagicMock()
    ollama.is_available.return_value = True
    ollama.generate.side_effect = RuntimeError("model down")
    gen = CoverLetterGenerator(mock_selector, mock_voice, ollama, mock_loader)
    result = gen.generate("Python engineer role", "Acme", "SWE", "medium")
    assert isinstance(result["text"], str)
    assert "Acme" in result["text"]  # template always includes company name


def test_generate_returns_word_count(mock_selector, mock_voice, mock_loader):
    ollama = MagicMock()
    ollama.is_available.return_value = False
    gen = CoverLetterGenerator(mock_selector, mock_voice, ollama, mock_loader)
    result = gen.generate("Python role", "Acme", "SWE", "long")
    assert result["word_count"] == len(result["text"].split())
    assert result["length_target"] == "long"
