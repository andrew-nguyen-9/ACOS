import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from backend.services.ollama_client import OllamaClient

logger = logging.getLogger(__name__)


class Embedder:
    def __init__(self, ollama_client: "OllamaClient", model: str) -> None:
        self._client = ollama_client
        self._model = model

    def embed(self, text: str) -> list[float]:
        return self._client.embed(model=self._model, text=text)

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        results = []
        for text in texts:
            results.append(self.embed(text))
        return results
