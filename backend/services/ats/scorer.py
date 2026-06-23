from __future__ import annotations

import json
import logging
import re
from collections.abc import Mapping
from typing import Any, cast

from backend.config import get_settings
from backend.observability import log_operation

logger = logging.getLogger(__name__)

# 12.8 Spike A — ATS score schema. Scores are integers; keyword lists are open
# arrays. Constrains shape only, so the model fills values it derives.
_ATS_SCHEMA: dict = {
    "type": "object",
    "properties": {
        "overall_score": {"type": "integer"},
        "keyword_score": {"type": "integer"},
        "skill_score": {"type": "integer"},
        "experience_score": {"type": "integer"},
        "industry_score": {"type": "integer"},
        "matched_keywords": {"type": "array"},
        "missing_keywords": {"type": "array"},
        "explanation": {"type": "string"},
    },
    "required": ["overall_score", "explanation"],
}

_DEFAULT_RESULT: dict[str, object] = {
    "overall_score": 0,
    "keyword_score": 0,
    "skill_score": 0,
    "experience_score": 0,
    "industry_score": 0,
    "matched_keywords": [],
    "missing_keywords": [],
    "explanation": "Scoring unavailable.",
}


def _clamp(value: int | float) -> int:
    return max(0, min(100, int(value)))


class ATSScorer:
    # ollama_client and prompt_loader are duck-typed; Any avoids Protocol overhead
    def __init__(self, ollama_client: Any, prompt_loader: Any) -> None:
        self._ollama = ollama_client
        self._loader = prompt_loader

    def score(
        self,
        resume_text: str,
        job_description: str,
        keywords: Mapping[str, object],
        *,
        seed: int | None = None,
    ) -> dict[str, object]:
        if self._ollama and self._ollama.is_available():
            result = self._llm_score(resume_text, job_description, seed=seed)
        else:
            result = self._keyword_score(resume_text, keywords)
        log_operation("ats_score", overall=result.get("overall_score", 0))
        return result

    def _llm_score(
        self, resume_text: str, job_description: str, *, seed: int | None = None
    ) -> dict[str, object]:
        try:
            prompt_data = self._loader.load("resume/score_ats")
            user = prompt_data["user_template"].format(
                job_description=job_description[:3000],
                resume_text=resume_text[:3000],
            )
            fmt = _ATS_SCHEMA if get_settings().enable_structured_output else None
            raw = self._ollama.generate(
                model=None,
                prompt=user,
                temperature=0.1,
                system=prompt_data["system"],
                output_format=fmt,
                think=False if fmt else None,
                seed=seed,
            )
            data = json.loads(raw)
            return {
                "overall_score": _clamp(data.get("overall_score", 0)),
                "keyword_score": _clamp(data.get("keyword_score", 0)),
                "skill_score": _clamp(data.get("skill_score", 0)),
                "experience_score": _clamp(data.get("experience_score", 0)),
                "industry_score": _clamp(data.get("industry_score", 0)),
                "matched_keywords": data.get("matched_keywords", []),
                "missing_keywords": data.get("missing_keywords", []),
                "explanation": data.get("explanation", ""),
            }
        except json.JSONDecodeError as exc:
            logger.warning("ats_scorer: invalid JSON from LLM: %s", exc)
            return dict(_DEFAULT_RESULT) | {"explanation": "LLM returned invalid response."}
        except Exception as exc:
            logger.warning("ats_scorer: LLM failed: %s", exc)
            return dict(_DEFAULT_RESULT) | {"explanation": str(exc)}

    def _keyword_score(self, resume_text: str, keywords: Mapping[str, object]) -> dict[str, object]:
        required = cast(list[str], keywords.get("required_skills", []))
        all_kw_raw = cast(list[str], keywords.get("keywords", []))
        all_kw = [k.lower() for k in required] + [k.lower() for k in all_kw_raw]
        resume_lower = resume_text.lower()
        matched = [k for k in all_kw if re.search(r"\b" + re.escape(k) + r"\b", resume_lower)]
        missing = [k for k in all_kw if k not in matched]
        score = int(100 * len(matched) / len(all_kw)) if all_kw else 0
        return {
            "overall_score": score,
            "keyword_score": score,
            "skill_score": score,
            "experience_score": score,
            "industry_score": 50,
            "matched_keywords": matched,
            "missing_keywords": missing,
            "explanation": f"Pattern-based score: {len(matched)}/{len(all_kw)} keywords matched.",
        }
