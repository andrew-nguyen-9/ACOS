import pytest
import respx
import httpx

from backend.services.ollama_client import OllamaClient

BASE = "http://localhost:11434"


@pytest.fixture
def client():
    return OllamaClient(base_url=BASE, timeout=10)


def test_is_available_returns_true_when_tags_200(client):
    with respx.mock:
        respx.get(f"{BASE}/api/tags").mock(return_value=httpx.Response(200, json={"models": []}))
        assert client.is_available() is True


def test_is_available_returns_false_on_connection_error(client):
    with respx.mock:
        respx.get(f"{BASE}/api/tags").mock(side_effect=httpx.ConnectError("refused"))
        assert client.is_available() is False


def test_generate_returns_response_text(client):
    with respx.mock:
        respx.post(f"{BASE}/api/generate").mock(
            return_value=httpx.Response(200, json={"response": "Generated text."})
        )
        result = client.generate(model="qwen3:8b", prompt="Hello")
        assert result == "Generated text."


def test_generate_passes_temperature(client):
    with respx.mock:
        route = respx.post(f"{BASE}/api/generate").mock(
            return_value=httpx.Response(200, json={"response": "ok"})
        )
        client.generate(model="qwen3:8b", prompt="Test", temperature=0.1)
        sent = route.calls[0].request
        import json
        body = json.loads(sent.content)
        assert body["options"]["temperature"] == 0.1


def test_embed_returns_float_list(client):
    fake_embedding = [0.1, 0.2, 0.3] * 256
    with respx.mock:
        respx.post(f"{BASE}/api/embeddings").mock(
            return_value=httpx.Response(200, json={"embedding": fake_embedding})
        )
        result = client.embed(model="nomic-embed-text", text="Some text")
        assert result == fake_embedding
        assert isinstance(result[0], float)


def test_list_models_returns_model_names(client):
    with respx.mock:
        respx.get(f"{BASE}/api/tags").mock(
            return_value=httpx.Response(
                200,
                json={"models": [{"name": "qwen3:8b"}, {"name": "nomic-embed-text"}]},
            )
        )
        models = client.list_models()
        assert "qwen3:8b" in models
        assert "nomic-embed-text" in models


def test_list_models_returns_empty_on_error(client):
    with respx.mock:
        respx.get(f"{BASE}/api/tags").mock(side_effect=httpx.ConnectError("refused"))
        assert client.list_models() == []
