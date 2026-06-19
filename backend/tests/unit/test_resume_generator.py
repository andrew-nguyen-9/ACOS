import json
from unittest.mock import MagicMock
import pytest
from backend.services.resume.generator import ResumeGenerator


@pytest.fixture
def mock_evidence_selector():
    sel = MagicMock()
    sel.select.return_value = [
        {
            "bullet_text": "Built Python ETL pipeline reducing processing time by 40%",
            "evidence_id": "b1",
            "experience_id": "exp1",
            "company": "Acme Corp",
            "title": "Data Engineer",
            "dates": "2022-01–2024-01",
            "confidence": "verified",
        }
    ]
    return sel


@pytest.fixture
def mock_kw_extractor():
    ext = MagicMock()
    ext.extract.return_value = {
        "required_skills": ["Python", "ETL"],
        "preferred_skills": [],
        "keywords": ["data pipeline", "Python"],
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
        "matched_keywords": ["Python", "ETL"],
        "missing_keywords": [],
        "explanation": "Strong match.",
    }
    return scorer


@pytest.fixture
def mock_ollama():
    client = MagicMock()
    client.is_available.return_value = True
    client.generate.return_value = json.dumps({
        "experiences": [{"title": "Data Engineer", "company": "Acme Corp", "dates": "2022–2024",
                         "bullets": [{"text": "Built Python ETL pipeline", "evidence_id": "b1", "confidence": "verified"}]}],
        "skills": ["Python", "ETL", "SQL"],
        "projects": [],
        "education": [],
    })
    return client


@pytest.fixture
def mock_loader():
    loader = MagicMock()
    loader.load.return_value = {
        "version": "1.0",
        "system": "Generate resume",
        "user_template": "JD: {job_description}\nTemplate: {template_name}\nKeywords: {keywords}\nEvidence: {evidence_json}",
    }
    return loader


def test_generate_returns_required_keys(
    mock_evidence_selector, mock_kw_extractor, mock_ats_scorer,
    mock_ollama, mock_loader, test_session
):
    gen = ResumeGenerator(
        mock_evidence_selector, mock_kw_extractor, mock_ats_scorer,
        mock_ollama, mock_loader, test_session
    )
    result = gen.generate("Python data engineering role at Acme", "software")
    for key in ["resume_id", "content_json", "ats_score", "weak_inference_count", "requires_approval"]:
        assert key in result


def test_generate_no_weak_inference_no_approval(
    mock_evidence_selector, mock_kw_extractor, mock_ats_scorer,
    mock_ollama, mock_loader, test_session
):
    gen = ResumeGenerator(
        mock_evidence_selector, mock_kw_extractor, mock_ats_scorer,
        mock_ollama, mock_loader, test_session
    )
    result = gen.generate("Python role", "software")
    assert result["weak_inference_count"] == 0
    assert result["requires_approval"] is False


def test_generate_weak_inference_sets_approval(
    mock_kw_extractor, mock_ats_scorer, mock_ollama, mock_loader, test_session
):
    sel = MagicMock()
    sel.select.return_value = [
        {
            "bullet_text": "Possibly led a team",
            "evidence_id": "w1",
            "experience_id": "exp1",
            "company": "Corp",
            "title": "Manager",
            "dates": "2020–2021",
            "confidence": "weak_inference",
        }
    ]
    gen = ResumeGenerator(sel, mock_kw_extractor, mock_ats_scorer, mock_ollama, mock_loader, test_session)
    result = gen.generate("Management role", "consulting")
    assert result["requires_approval"] is True


def test_generate_saves_resume_to_db(
    mock_evidence_selector, mock_kw_extractor, mock_ats_scorer,
    mock_ollama, mock_loader, test_session
):
    gen = ResumeGenerator(
        mock_evidence_selector, mock_kw_extractor, mock_ats_scorer,
        mock_ollama, mock_loader, test_session
    )
    result = gen.generate("Python role", "software")
    assert result["resume_id"] is not None
    assert len(result["resume_id"]) == 32
