from __future__ import annotations

from unittest.mock import patch


def test_ollama_health_reports_degraded_when_unavailable(client):
    with patch("backend.api.v1.routes.health.OllamaClient") as M:
        inst = M.return_value
        inst.is_available.return_value = False
        inst.list_models.return_value = []
        r = client.get("/api/v1/health/ollama")
    assert r.status_code == 200
    body = r.json()
    assert body["available"] is False
    assert body["degraded"] is True
    assert set(body["missing_models"]) == {"qwen3:8b", "nomic-embed-text"}


def test_ollama_health_reports_healthy_when_all_models_present(client):
    with patch("backend.api.v1.routes.health.OllamaClient") as M:
        inst = M.return_value
        inst.is_available.return_value = True
        inst.list_models.return_value = ["qwen3:8b", "nomic-embed-text:latest", "other"]
        r = client.get("/api/v1/health/ollama")
    body = r.json()
    assert body["available"] is True
    assert body["degraded"] is False
    assert body["missing_models"] == []


def test_ollama_health_partial_models_is_degraded(client):
    with patch("backend.api.v1.routes.health.OllamaClient") as M:
        inst = M.return_value
        inst.is_available.return_value = True
        inst.list_models.return_value = ["qwen3:8b"]
        r = client.get("/api/v1/health/ollama")
    body = r.json()
    assert body["degraded"] is True
    assert body["missing_models"] == ["nomic-embed-text"]
