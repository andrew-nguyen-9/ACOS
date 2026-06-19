from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


def test_generate_cover_letter_returns_text(client):
    with (
        patch("backend.api.v1.routes.cover_letter.OllamaClient") as mock_cls,
        patch("backend.api.v1.routes.cover_letter.RAGRetriever") as mock_ret_cls,
        patch("backend.api.v1.routes.cover_letter.Reranker") as mock_rnk_cls,
    ):
        mock_ollama = MagicMock()
        mock_ollama.is_available.return_value = False
        mock_cls.return_value = mock_ollama
        mock_ret_cls.return_value = MagicMock()
        mock_ret_cls.return_value.retrieve.return_value = []
        mock_rnk_cls.return_value = MagicMock()
        mock_rnk_cls.return_value.rerank.return_value = []

        resp = client.post(
            "/api/v1/cover-letter/generate",
            json={
                "job_description": "Python engineer at Acme",
                "company": "Acme Corp",
                "job_title": "Software Engineer",
                "length_target": "medium",
            },
        )
    assert resp.status_code == 200
    data = resp.json()
    assert "text" in data
    assert "word_count" in data
    assert "requires_approval" in data
    assert "length_target" in data


def test_generate_cover_letter_invalid_length(client):
    resp = client.post(
        "/api/v1/cover-letter/generate",
        json={
            "job_description": "Python role",
            "company": "Co",
            "job_title": "Dev",
            "length_target": "gigantic",
        },
    )
    assert resp.status_code == 422


def test_generate_cover_letter_download_returns_docx(client):
    with (
        patch("backend.api.v1.routes.cover_letter.OllamaClient") as mock_cls,
        patch("backend.api.v1.routes.cover_letter.RAGRetriever") as mock_ret_cls,
        patch("backend.api.v1.routes.cover_letter.Reranker") as mock_rnk_cls,
    ):
        mock_ollama = MagicMock()
        mock_ollama.is_available.return_value = False
        mock_cls.return_value = mock_ollama
        mock_ret_cls.return_value = MagicMock()
        mock_ret_cls.return_value.retrieve.return_value = []
        mock_rnk_cls.return_value = MagicMock()
        mock_rnk_cls.return_value.rerank.return_value = []

        resp = client.post(
            "/api/v1/cover-letter/generate/download",
            json={
                "job_description": "Python engineer at Acme",
                "company": "Acme Corp",
                "job_title": "Software Engineer",
                "length_target": "short",
            },
        )
    assert resp.status_code == 200
    assert (
        resp.headers["content-type"]
        == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )
    assert len(resp.content) > 0


def test_generate_cover_letter_download_invalid_length(client):
    resp = client.post(
        "/api/v1/cover-letter/generate/download",
        json={
            "job_description": "Python role",
            "company": "Co",
            "job_title": "Dev",
            "length_target": "gigantic",
        },
    )
    assert resp.status_code == 422


def test_learn_voice_returns_profile(client):
    with patch("backend.api.v1.routes.cover_letter.OllamaClient") as mock_cls:
        mock_ollama = MagicMock()
        mock_ollama.is_available.return_value = False
        mock_cls.return_value = mock_ollama

        resp = client.post(
            "/api/v1/cover-letter/learn-voice",
            json={
                "texts": [
                    "Dear Hiring Manager, I am excited to apply for this role."
                ]
            },
        )
    assert resp.status_code == 200
    data = resp.json()
    assert "tone_descriptors" in data
