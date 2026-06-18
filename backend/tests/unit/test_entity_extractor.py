import json
from unittest.mock import MagicMock

import pytest

from backend.ingestion.entity_extractor import EntityExtractor


@pytest.fixture
def mock_ollama():
    client = MagicMock()
    return client


def test_extract_returns_dict_structure(mock_ollama):
    mock_ollama.generate.return_value = json.dumps({
        "skills": [{"name": "Python", "confidence": "strong_inference"}],
        "experiences": [],
        "projects": [],
    })
    extractor = EntityExtractor(mock_ollama)
    result = extractor.extract("Python developer with 5 years experience", "resume")
    assert "skills" in result
    assert "experiences" in result
    assert "projects" in result


def test_extract_malformed_json_returns_empty(mock_ollama):
    mock_ollama.generate.return_value = "not json at all"
    extractor = EntityExtractor(mock_ollama)
    result = extractor.extract("some text", "resume")
    assert result == {"skills": [], "experiences": [], "projects": []}


def test_extract_pattern_skills_do_not_need_llm():
    """Pattern-matched known skills should be strong_inference without LLM."""
    extractor = EntityExtractor(ollama_client=None)
    result = extractor.extract_patterns("Experienced in Python, SQL, and FastAPI.")
    skill_names = [s["name"].lower() for s in result["skills"]]
    assert "python" in skill_names
    assert "sql" in skill_names
    # All pattern matches are strong_inference
    assert all(s["confidence"] == "strong_inference" for s in result["skills"])
