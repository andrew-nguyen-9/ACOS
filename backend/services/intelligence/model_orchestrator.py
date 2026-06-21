from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

_DEFAULT_MODEL = "qwen3:8b"

# mode → (temperature, max_tokens). One local model, tuned per task shape.
# ponytail: num_ctx not set — OllamaClient.generate exposes no context window;
# add a num_ctx passthrough only if long-context truncation actually bites.
_MODE_CONFIG: dict[str, tuple[float, int]] = {
    "fast_retrieval": (0.0, 512),
    "deep_reasoning": (0.1, 2048),
    "ats_optimization": (0.0, 1024),
    "copilot": (0.4, 4096),
}


class ModelOrchestrator:
    """Route a generation task to the right Ollama config for its mode.

    Returns None when Ollama is unavailable so callers fall back deterministically.
    """

    def __init__(self, ollama_client: Any, model: str = _DEFAULT_MODEL) -> None:
        self._ollama = ollama_client
        self._model = model

    def run(self, mode: str, prompt: str, system: str | None = None) -> str | None:
        if mode not in _MODE_CONFIG:
            raise ValueError(f"Unknown mode '{mode}'. Valid: {list(_MODE_CONFIG)}")
        if not self._ollama or not self._ollama.is_available():
            return None
        temperature, max_tokens = _MODE_CONFIG[mode]
        return self._ollama.generate(
            model=self._model,
            prompt=prompt,
            temperature=temperature,
            max_tokens=max_tokens,
            system=system,
        )
