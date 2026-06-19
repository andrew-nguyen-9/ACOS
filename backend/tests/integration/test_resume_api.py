from unittest.mock import patch, MagicMock

from fastapi.testclient import TestClient


def test_analyze_ats_returns_score_and_keywords(client: TestClient) -> None:
    """POST /api/v1/resume/analyze-ats returns 200 with ats_score and keywords keys.

    OllamaClient is patched to be unavailable so the keyword-fallback path is exercised
    without requiring a running Ollama instance.
    """
    mock_ollama = MagicMock()
    mock_ollama.is_available.return_value = False

    with patch(
        "backend.api.v1.routes.resume.OllamaClient",
        return_value=mock_ollama,
    ):
        response = client.post(
            "/api/v1/resume/analyze-ats",
            json={
                "resume_text": "Python developer with SQL and ETL experience.",
                "job_description": "We need a Python developer with SQL skills and ETL pipeline experience.",
            },
        )

    assert response.status_code == 200
    data = response.json()
    assert "ats_score" in data
    assert "keywords" in data
    assert isinstance(data["ats_score"]["overall_score"], int)
    assert isinstance(data["keywords"], dict)
