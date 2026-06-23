from __future__ import annotations

import json
import logging
import re
from pathlib import Path

import yaml

from backend.config import get_settings
from backend.services.ollama_client import OllamaClient

logger = logging.getLogger(__name__)

_PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "extract_entities.yaml"

# 12.8 Spike A — structure-only schema: guarantees the three array keys exist as
# arrays. Item shapes stay open so the model never invents required fields
# (no-hallucination); confidence still traces to evidence as before.
_EXTRACT_SCHEMA: dict = {
    "type": "object",
    "properties": {
        "skills": {"type": "array"},
        "experiences": {"type": "array"},
        "projects": {"type": "array"},
    },
    "required": ["skills", "experiences", "projects"],
}

# Known skill ontology for pattern-based strong_inference matching
_KNOWN_SKILLS: frozenset[str] = frozenset({
    "python", "sql", "fastapi", "sqlalchemy", "react", "typescript",
    "javascript", "tauri", "chromadb", "ollama", "pydantic", "alembic",
    "postgresql", "sqlite", "pandas", "numpy", "scikit-learn", "docker",
    "kubernetes", "terraform", "aws", "gcp", "azure", "git", "github",
    "jira", "confluence", "figma", "tableau", "power bi", "excel",
    "java", "go", "rust", "c++", "c#", "ruby", "php", "bash", "linux",
    "machine learning", "deep learning", "nlp", "rag", "llm",
})

_EMPTY: dict[str, list] = {"skills": [], "experiences": [], "projects": []}


def _load_prompt() -> dict:
    with _PROMPT_PATH.open() as f:
        return yaml.safe_load(f)


class EntityExtractor:
    def __init__(self, ollama_client: OllamaClient | None) -> None:
        self._ollama = ollama_client
        self._prompt = _load_prompt() if _PROMPT_PATH.exists() else {}

    def extract_patterns(self, text: str) -> dict:
        """Extract skills using regex against the known skill ontology.

        All matched skills receive ``strong_inference`` confidence.
        Does not require a live Ollama connection.
        """
        text_lower = text.lower()
        found_skills: list[dict] = []
        for skill in sorted(_KNOWN_SKILLS):  # sorted for deterministic ordering
            pattern = r"\b" + re.escape(skill) + r"\b"
            if re.search(pattern, text_lower):
                found_skills.append({"name": skill, "confidence": "strong_inference"})
        return {"skills": found_skills, "experiences": [], "projects": []}

    def extract(self, text: str, document_type: str) -> dict:
        """Extract career entities from *text*.

        Uses Ollama for LLM-based extraction when available; falls back to
        pattern matching when ``ollama_client`` is ``None``.
        """
        if not self._ollama:
            return self.extract_patterns(text)

        system = self._prompt.get("system", "")
        user_tmpl = self._prompt.get("user_template", "{text}")
        user = user_tmpl.format(document_type=document_type, text=text[:6000])

        fmt = _EXTRACT_SCHEMA if get_settings().enable_structured_output else None
        try:
            raw = self._ollama.generate(
                model="qwen3:8b",
                prompt=user,
                temperature=0.1,
                system=system,
                output_format=fmt,
                think=False if fmt else None,  # schema constraint vs qwen3 reasoning
            )
            data = json.loads(raw)
            return {
                "skills": data.get("skills", []),
                "experiences": data.get("experiences", []),
                "projects": data.get("projects", []),
            }
        except json.JSONDecodeError as exc:
            logger.warning("entity_extractor: LLM returned invalid JSON: %s", exc)
            return dict(_EMPTY)
        except Exception as exc:
            logger.warning("entity_extractor: LLM call failed, falling back to patterns: %s", exc)
            return self.extract_patterns(text)
