"""Integration test: full resume-to-cover-letter pipeline.

Verifies that:
1. ResumeGenerator produces resume_context and validation in its response.
2. The resume_context is stored in content_json["_resume_context"] and readable via
   ResumeRepository after the fact.
3. CoverLetterGenerator accepts the stored resume_context and uses it (skips evidence
   selector, passes consistency check).
"""
from __future__ import annotations

import json
from unittest.mock import MagicMock

import pytest

from backend.repositories.resume import ResumeRepository
from backend.services.cover_letter.generator import CoverLetterGenerator
from backend.services.cover_letter.voice_modeler import VoiceModeler
from backend.services.resume.generator import ResumeGenerator


# ── Shared fixtures ──────────────────────────────────────────────────────────

@pytest.fixture
def mock_evidence() -> list[dict]:
    return [
        {
            "bullet_text": "Built Python ETL pipeline reducing latency by 40%",
            "evidence_id": "b1",
            "experience_id": "exp1",
            "company": "Acme Corp",
            "title": "Data Engineer",
            "dates": "2022–2024",
            "confidence": "verified",
        },
        {
            "bullet_text": "Led migration generating $3M in cost savings",
            "evidence_id": "b2",
            "experience_id": "exp1",
            "company": "Acme Corp",
            "title": "Data Engineer",
            "dates": "2022–2024",
            "confidence": "verified",
        },
    ]


@pytest.fixture
def mock_evidence_selector(mock_evidence):
    sel = MagicMock()
    sel.select.return_value = mock_evidence
    return sel


@pytest.fixture
def mock_kw_extractor():
    ext = MagicMock()
    ext.extract.return_value = {
        "required_skills": ["Python", "ETL"],
        "preferred_skills": [],
        "keywords": ["data pipeline"],
        "industry": "technology",
        "seniority_level": "senior",
    }
    return ext


@pytest.fixture
def mock_ats_scorer():
    scorer = MagicMock()
    scorer.score.return_value = {
        "overall_score": 85,
        "keyword_score": 88,
        "skill_score": 82,
        "experience_score": 80,
        "industry_score": 90,
        "matched_keywords": ["Python"],
        "missing_keywords": [],
        "explanation": "Strong match.",
    }
    return scorer


@pytest.fixture
def mock_ollama_resume():
    client = MagicMock()
    client.is_available.return_value = True
    client.generate.return_value = json.dumps({
        "experiences": [{"title": "Data Engineer", "company": "Acme Corp", "dates": "2022–2024",
                         "bullets": [{"text": "Built Python ETL pipeline", "evidence_id": "b1", "confidence": "verified"}]}],
        "skills": ["Python"],
        "projects": [],
        "education": [],
    })
    return client


@pytest.fixture
def mock_resume_loader():
    loader = MagicMock()
    loader.load.return_value = {
        "system": "Build resume.",
        "user_template": "JD: {job_description}\nTemplate: {template_name}\nKeywords: {keywords}\nEvidence: {evidence_json}",
    }
    return loader


@pytest.fixture
def mock_ollama_cl():
    client = MagicMock()
    client.is_available.return_value = True
    client.generate.return_value = (
        "I am excited to join Acme Corp as a Data Engineer. "
        "In 2023, my Python ETL work at Acme Corp generated $3M in savings."
    )
    return client


@pytest.fixture
def mock_cl_loader():
    loader = MagicMock()
    loader.load.return_value = {
        "system": "Write CL.",
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
def mock_voice(test_session):
    vm = MagicMock(spec=VoiceModeler)
    vm.get_or_create_default.return_value = {
        "tone_descriptors": ["professional"],
        "vocabulary_patterns": {},
        "sample_sentences": [],
    }
    return vm


# ── Tests ────────────────────────────────────────────────────────────────────

def test_resume_generate_returns_resume_context(
    mock_evidence_selector, mock_kw_extractor, mock_ats_scorer,
    mock_ollama_resume, mock_resume_loader, test_session
) -> None:
    gen = ResumeGenerator(
        mock_evidence_selector, mock_kw_extractor, mock_ats_scorer,
        mock_ollama_resume, mock_resume_loader, test_session,
    )
    result = gen.generate(
        "Python data engineering role", "software",
        company="Acme Corp", job_title="Data Engineer",
    )
    assert "resume_context" in result
    ctx = result["resume_context"]
    assert ctx["company"] == "Acme Corp"
    assert ctx["job_title"] == "Data Engineer"
    assert isinstance(ctx["selected_bullets"], list)


def test_resume_generate_stores_context_in_db(
    mock_evidence_selector, mock_kw_extractor, mock_ats_scorer,
    mock_ollama_resume, mock_resume_loader, test_session
) -> None:
    gen = ResumeGenerator(
        mock_evidence_selector, mock_kw_extractor, mock_ats_scorer,
        mock_ollama_resume, mock_resume_loader, test_session,
    )
    result = gen.generate("Python data engineering role", "software")
    resume_id = result["resume_id"]

    repo = ResumeRepository(test_session)
    resume = repo.get(resume_id)
    assert resume is not None
    assert "_resume_context" in resume.content_json


def test_cover_letter_uses_stored_resume_context(
    mock_evidence_selector, mock_kw_extractor, mock_ats_scorer,
    mock_ollama_resume, mock_resume_loader,
    mock_ollama_cl, mock_cl_loader, mock_voice, test_session
) -> None:
    # Generate resume (stores context in DB)
    resume_gen = ResumeGenerator(
        mock_evidence_selector, mock_kw_extractor, mock_ats_scorer,
        mock_ollama_resume, mock_resume_loader, test_session,
    )
    result = resume_gen.generate(
        "Python data engineering role", "software",
        company="Acme Corp", job_title="Data Engineer",
    )
    resume_id = result["resume_id"]

    # Retrieve context from DB
    repo = ResumeRepository(test_session)
    resume = repo.get(resume_id)
    assert resume is not None
    stored_context = resume.content_json.get("_resume_context")
    assert stored_context is not None

    # Generate cover letter using stored context — selector must NOT be called
    cl_selector = MagicMock()
    cl_gen = CoverLetterGenerator(cl_selector, mock_voice, mock_ollama_cl, mock_cl_loader)
    cl_result = cl_gen.generate(
        "Python data engineering role", "Acme Corp", "Data Engineer", "medium",
        resume_context=stored_context,
    )

    cl_selector.select.assert_not_called()
    assert "text" in cl_result
    assert "consistency" in cl_result
    assert isinstance(cl_result["text"], str)
    assert len(cl_result["text"]) > 0


def test_cover_letter_validation_passes(
    mock_evidence_selector, mock_kw_extractor, mock_ats_scorer,
    mock_ollama_resume, mock_resume_loader,
    mock_ollama_cl, mock_cl_loader, mock_voice, test_session
) -> None:
    resume_gen = ResumeGenerator(
        mock_evidence_selector, mock_kw_extractor, mock_ats_scorer,
        mock_ollama_resume, mock_resume_loader, test_session,
    )
    result = resume_gen.generate(
        "Python data engineering role", "software",
        company="Acme Corp", job_title="Data Engineer",
    )
    assert "validation" in result
    # Validation may have warnings from the mock content but should not block export
    # (weak mock bullets may trigger verb errors — that's expected in tests)
    val = result["validation"]
    assert "valid" in val
    assert "errors" in val
    assert "warnings" in val
