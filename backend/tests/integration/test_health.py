def test_health_returns_200(client):
    resp = client.get("/api/v1/health")
    assert resp.status_code == 200


def test_health_response_structure(client):
    resp = client.get("/api/v1/health")
    body = resp.json()
    assert body["status"] in ("ok", "degraded")
    assert body["db"] in ("connected", "error")
    assert "version" in body


def test_health_returns_200_when_db_connected(client):
    resp = client.get("/api/v1/health")
    body = resp.json()
    assert body["db"] == "connected"
    assert resp.status_code == 200
    assert body["status"] == "ok"


def test_health_ollama_returns_200(client):
    resp = client.get("/api/v1/health/ollama")
    assert resp.status_code == 200


def test_health_ollama_response_structure(client):
    resp = client.get("/api/v1/health/ollama")
    body = resp.json()
    assert "available" in body
    assert isinstance(body["available"], bool)
    assert isinstance(body["models"], list)
