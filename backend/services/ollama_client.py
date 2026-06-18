import logging

import httpx

logger = logging.getLogger(__name__)

_GENERATE_PATH = "/api/generate"
_EMBED_PATH = "/api/embeddings"
_TAGS_PATH = "/api/tags"


class OllamaClient:
    def __init__(self, base_url: str = "http://localhost:11434", timeout: int = 120) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout

    def is_available(self) -> bool:
        try:
            resp = httpx.get(f"{self._base_url}/api/tags", timeout=5)
            return resp.status_code == 200
        except Exception:
            return False

    def generate(
        self,
        model: str,
        prompt: str,
        temperature: float = 0.3,
        max_tokens: int | None = None,
        system: str | None = None,
    ) -> str:
        payload: dict = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": temperature},
        }
        if max_tokens is not None:
            payload["options"]["num_predict"] = max_tokens
        if system is not None:
            payload["system"] = system

        resp = httpx.post(
            f"{self._base_url}{_GENERATE_PATH}",
            json=payload,
            timeout=self._timeout,
        )
        resp.raise_for_status()
        return resp.json()["response"]

    def embed(self, model: str, text: str) -> list[float]:
        resp = httpx.post(
            f"{self._base_url}{_EMBED_PATH}",
            json={"model": model, "prompt": text},
            timeout=self._timeout,
        )
        resp.raise_for_status()
        return resp.json()["embedding"]

    def list_models(self) -> list[str]:
        try:
            resp = httpx.get(f"{self._base_url}{_TAGS_PATH}", timeout=10)
            resp.raise_for_status()
            return [m["name"] for m in resp.json().get("models", [])]
        except Exception as exc:
            logger.warning("list_models failed: %s", exc)
            return []
