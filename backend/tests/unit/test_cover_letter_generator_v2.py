from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from backend.services.cover_letter.generator import CoverLetterGenerator


@pytest.fixture
def mock_voice():
    vm = MagicMock()
    vm.get_or_create_default.return_value = {
        "tone_descriptors": ["professional"],
        "vocabulary_patterns": {},
        "sample_sentences": [],
    }
    return vm


@pytest.fixture
def mock_loader():
    loader = MagicMock()
    loader.load.return_value = {
        "system": "Write cover letter.",
        "user_template": (
            "JD: {job_description}\nCompany: {company}\nTitle: {job_title}\n"
            "Length: {length_target}\nEvidence: {evidence_json}\nKeywords: {keywords}\n"
            "Tone: {tone_descriptors}\nVocab: {vocabulary_patterns}\n"
            "Samples: {sample_sentences}\nIndustry: {industry}\n"
            "Selected: {selected_bullets_json}\nExcluded: {excluded_bullets_json}"
        ),
    }
    return loader


@pytest.fixture
def mock_ollama():
    client = MagicMock()
    client.is_available.return_value = True
    client.generate.return_value = "I am excited to join Acme Corp. In 2023 I built pipelines."
    return client


@pytest.fixture
def sample_resume_context() -> dict:
    return {
        "resume_id": "abc123",
        "job_title": "Data Engineer",
        "company": "Acme Corp",
        "keywords": ["Python", "ETL"],
        "selected_bullets": [
            {
                "bullet_text": "Built Python ETL pipeline reducing latency by 40%",
                "company": "Acme Corp",
                "title": "Data Engineer",
                "dates": "2022–2024",
                "confidence": "verified",
                "score": 0.85,
            }
        ],
        "excluded_bullets": [
            {
                "bullet_text": "Helped with documentation",
                "company": "Acme Corp",
                "confidence": "weak_inference",
                "score": 0.2,
            }
        ],
    }


# ── resume_context wiring ────────────────────────────────────────────────────

def test_generate_with_resume_context_skips_selector(
    mock_voice, mock_loader, mock_ollama, sample_resume_context
) -> None:
    selector = MagicMock()
    gen = CoverLetterGenerator(selector, mock_voice, mock_ollama, mock_loader)
    gen.generate("Python role", "Acme Corp", "Data Engineer", "medium",
                 resume_context=sample_resume_context)
    selector.select.assert_not_called()


def test_generate_without_resume_context_calls_selector(
    mock_voice, mock_loader, mock_ollama
) -> None:
    selector = MagicMock()
    selector.select.return_value = []
    gen = CoverLetterGenerator(selector, mock_voice, mock_ollama, mock_loader)
    gen.generate("Python role", "Acme Corp", "Data Engineer", "medium")
    selector.select.assert_called_once()


def test_generate_returns_consistency_key(
    mock_voice, mock_loader, mock_ollama, sample_resume_context
) -> None:
    gen = CoverLetterGenerator(MagicMock(), mock_voice, mock_ollama, mock_loader)
    result = gen.generate("Python role", "Acme Corp", "Data Engineer", "medium",
                          resume_context=sample_resume_context)
    assert "consistency" in result
    assert "consistent" in result["consistency"]
    assert "warnings" in result["consistency"]


def test_generate_weak_excluded_bullet_does_not_set_approval(
    mock_voice, mock_loader, mock_ollama, sample_resume_context
) -> None:
    gen = CoverLetterGenerator(MagicMock(), mock_voice, mock_ollama, mock_loader)
    result = gen.generate("Python role", "Acme Corp", "Data Engineer", "medium",
                          resume_context=sample_resume_context)
    # Approval is driven by selected bullets only (weak_inference in excluded doesn't count)
    assert result["requires_approval"] is False
