import json
from unittest.mock import MagicMock
import pytest
from backend.services.ats.scorer import ATSScorer


@pytest.fixture
def mock_ollama():
    client = MagicMock()
    client.is_available.return_value = True
    client.generate.return_value = json.dumps({
        "overall_score": 82,
        "keyword_score": 85,
        "skill_score": 80,
        "experience_score": 78,
        "industry_score": 90,
        "matched_keywords": ["Python", "SQL", "pipeline"],
        "missing_keywords": ["Spark"],
        "explanation": "Strong Python match but missing big data skills.",
    })
    return client


@pytest.fixture
def mock_loader():
    loader = MagicMock()
    loader.load.return_value = {
        "version": "1.0",
        "system": "Score the resume.",
        "user_template": "JD:\n{job_description}\n\nResume:\n{resume_text}\n\nReturn JSON.",
    }
    return loader


def test_score_returns_all_keys(mock_ollama, mock_loader):
    scorer = ATSScorer(mock_ollama, mock_loader)
    result = scorer.score("Python developer resume text.", "Senior Python role", {})
    for key in ["overall_score", "keyword_score", "skill_score", "experience_score",
                "industry_score", "matched_keywords", "missing_keywords", "explanation"]:
        assert key in result


def test_score_clamps_between_0_and_100(mock_ollama, mock_loader):
    mock_ollama.generate.return_value = json.dumps({
        "overall_score": 150,
        "keyword_score": -5,
        "skill_score": 80,
        "experience_score": 80,
        "industry_score": 80,
        "matched_keywords": [],
        "missing_keywords": [],
        "explanation": "test",
    })
    scorer = ATSScorer(mock_ollama, mock_loader)
    result = scorer.score("resume", "jd", {})
    assert result["overall_score"] == 100
    assert result["keyword_score"] == 0


def test_score_keyword_fallback_no_llm(mock_loader):
    offline = MagicMock()
    offline.is_available.return_value = False
    scorer = ATSScorer(offline, mock_loader)
    keywords = {"required_skills": ["Python", "SQL"], "keywords": ["ETL", "Python"]}
    result = scorer.score("Python developer with SQL experience and ETL work.", "Python SQL ETL job", keywords)
    assert result["overall_score"] >= 0
    assert isinstance(result["matched_keywords"], list)


def test_score_malformed_json_returns_defaults(mock_ollama, mock_loader):
    mock_ollama.generate.return_value = "not json"
    scorer = ATSScorer(mock_ollama, mock_loader)
    result = scorer.score("resume", "jd", {})
    assert result["overall_score"] == 0
    assert result["explanation"] != ""
