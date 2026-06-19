from __future__ import annotations

import json
import logging
import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from backend.services.ollama_client import OllamaClient
    from backend.services.prompt_loader import PromptLoader

logger = logging.getLogger(__name__)

_EMPTY: dict[str, list[str] | str] = {
    "required_skills": [],
    "preferred_skills": [],
    "keywords": [],
    "industry": "technology",
    "seniority_level": "mid",
}

_COMMON_SKILLS = re.compile(
    r"\b(python|sql|java|javascript|typescript|react|fastapi|postgresql|aws|docker|kubernetes|"
    r"machine learning|deep learning|nlp|pandas|numpy|scikit-learn|terraform|git|"
    r"data engineering|etl|pipeline|analytics|tableau|power bi|excel)\b",
    re.IGNORECASE,
)


class KeywordExtractor:
    def __init__(self, ollama_client: OllamaClient, prompt_loader: PromptLoader) -> None:
        self._ollama = ollama_client
        self._loader = prompt_loader

    def extract(self, job_description: str) -> dict[str, list[str] | str]:
        if not self._ollama or not self._ollama.is_available():
            return self._regex_fallback(job_description)
        try:
            prompt_data = self._loader.load("resume/extract_keywords")
            user = prompt_data["user_template"].format(job_description=job_description[:4000])
            raw = self._ollama.generate(
                model=None,
                prompt=user,
                temperature=0.1,
                system=prompt_data["system"],
            )
            data = json.loads(raw)
            return {
                "required_skills": data.get("required_skills", []),
                "preferred_skills": data.get("preferred_skills", []),
                "keywords": data.get("keywords", []),
                "industry": data.get("industry", "technology"),
                "seniority_level": data.get("seniority_level", "mid"),
            }
        except json.JSONDecodeError as exc:
            logger.warning("keyword_extractor: LLM returned invalid JSON: %s", exc)
            return dict(_EMPTY)
        except Exception as exc:
            logger.warning("keyword_extractor: LLM failed, using regex fallback: %s", exc)
            return self._regex_fallback(job_description)

    def _regex_fallback(self, text: str) -> dict[str, list[str] | str]:
        found = list({m.group(0).lower() for m in _COMMON_SKILLS.finditer(text)})
        return {
            "required_skills": found,
            "preferred_skills": [],
            "keywords": found,
            "industry": "technology",
            "seniority_level": "mid",
        }
