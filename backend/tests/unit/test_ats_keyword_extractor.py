import json
from unittest.mock import MagicMock
import pytest
from backend.services.ats.keyword_extractor import KeywordExtractor


@pytest.fixture
def mock_ollama():
    client = MagicMock()
    client.is_available.return_value = True
    client.generate.return_value = json.dumps({
        "required_skills": ["Python", "SQL"],
        "preferred_skills": ["FastAPI"],
        "keywords": ["data engineering", "pipeline", "ETL"],
        "industry": "technology",
        "seniority_level": "senior",
    })
    return client


@pytest.fixture
def mock_loader():
    loader = MagicMock()
    loader.load.return_value = {
        "version": "1.0",
        "system": "Extract keywords",
        "user_template": "Job Description:\n{job_description}\n\nReturn JSON.",
    }
    return loader


def test_extract_returns_required_keys(mock_ollama, mock_loader):
    extractor = KeywordExtractor(mock_ollama, mock_loader)
    result = extractor.extract("Senior Python Engineer at Tech Co.")
    assert "required_skills" in result
    assert "preferred_skills" in result
    assert "keywords" in result
    assert "industry" in result
    assert "seniority_level" in result


def test_extract_llm_called_with_jd(mock_ollama, mock_loader):
    extractor = KeywordExtractor(mock_ollama, mock_loader)
    extractor.extract("Build Python data pipelines using SQL and ETL tools.")
    mock_ollama.generate.assert_called_once()
    call_kwargs = mock_ollama.generate.call_args
    prompt_text = call_kwargs[1].get("prompt") or call_kwargs[0][1]
    assert "Python" in prompt_text or "ETL" in prompt_text


def test_extract_falls_back_on_llm_failure(mock_loader):
    offline = MagicMock()
    offline.is_available.return_value = False
    extractor = KeywordExtractor(offline, mock_loader)
    result = extractor.extract("We need Python and SQL skills.")
    assert isinstance(result["required_skills"], list)
    assert isinstance(result["keywords"], list)


def test_extract_malformed_json_returns_empty(mock_ollama, mock_loader):
    mock_ollama.generate.return_value = "not json"
    extractor = KeywordExtractor(mock_ollama, mock_loader)
    result = extractor.extract("Some JD text")
    assert result["required_skills"] == []
