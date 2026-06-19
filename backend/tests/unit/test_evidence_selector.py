from unittest.mock import MagicMock
import pytest
from backend.services.resume.evidence_selector import EvidenceSelector


@pytest.fixture
def mock_retriever():
    r = MagicMock()
    r.retrieve.return_value = [
        {
            "id": "b1",
            "text": "Built Python ETL pipeline processing 10M records daily",
            "metadata": {
                "confidence_level": "verified",
                "experience_id": "exp1",
                "company": "Acme Corp",
                "title": "Data Engineer",
                "start_date": "2022-01",
                "end_date": "2024-01",
                "entity_id": "b1",
            },
            "semantic_score": 0.92,
            "collection": "acos_experiences",
        }
    ]
    return r


@pytest.fixture
def mock_reranker():
    r = MagicMock()
    r.rerank.return_value = [
        {
            "id": "b1",
            "text": "Built Python ETL pipeline processing 10M records daily",
            "metadata": {
                "confidence_level": "verified",
                "experience_id": "exp1",
                "company": "Acme Corp",
                "title": "Data Engineer",
                "start_date": "2022-01",
                "end_date": "2024-01",
                "entity_id": "b1",
            },
            "semantic_score": 0.92,
            "combined_score": 1.1,
            "collection": "acos_experiences",
        }
    ]
    return r


def test_select_returns_bullets(mock_retriever, mock_reranker):
    selector = EvidenceSelector(mock_retriever, mock_reranker)
    results = selector.select("Python data engineer role", {"required_skills": ["Python"]})
    assert len(results) == 1
    assert results[0]["bullet_text"] == "Built Python ETL pipeline processing 10M records daily"


def test_select_includes_confidence(mock_retriever, mock_reranker):
    selector = EvidenceSelector(mock_retriever, mock_reranker)
    results = selector.select("Python role", {})
    assert results[0]["confidence"] == "verified"


def test_select_limits_to_max_bullets(mock_retriever, mock_reranker):
    # Return 10 results from reranker
    item = mock_reranker.rerank.return_value[0]
    mock_reranker.rerank.return_value = [
        {**item, "id": str(i), "metadata": {**item["metadata"], "entity_id": str(i)}}
        for i in range(10)
    ]
    selector = EvidenceSelector(mock_retriever, mock_reranker)
    results = selector.select("Python role", {}, max_bullets=3)
    assert len(results) <= 3
