import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from backend.services.ollama_client import OllamaClient

logger = logging.getLogger(__name__)

# ponytail: 128 is the spec ceiling; a constant, not a setting, until a real
# throughput measurement says otherwise.
_BATCH_SIZE = 128


class Embedder:
    def __init__(self, ollama_client: "OllamaClient", model: str) -> None:
        self._client = ollama_client
        self._model = model

    def embed(self, text: str) -> list[float]:
        return self._client.embed(model=self._model, text=text)

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """One HTTP call per ≤128-chunk; vectors returned in input order."""
        results: list[list[float]] = []
        for start in range(0, len(texts), _BATCH_SIZE):
            chunk = texts[start : start + _BATCH_SIZE]
            results.extend(self._client.embed_batch(model=self._model, texts=chunk))
        return results
