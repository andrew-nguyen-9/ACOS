from __future__ import annotations

import json
import logging
import re
from typing import Any

logger = logging.getLogger(__name__)

_DEFAULT_MODEL = "qwen3:8b"

# Role-type classification signals (fallback path). First match wins by priority order.
_ROLE_SIGNALS: list[tuple[str, list[str]]] = [
    ("product_management", ["product manager", "product management", "product roadmap", "roadmap"]),
    ("consulting", ["consultant", "consulting", "client engagement", "client outcomes", "engagement"]),
    ("data_analytics", ["data analyst", "data analytics", "dashboard", "business intelligence", "analytics"]),
    ("tpm_solutions", ["technical program", "program manager", "solutions architect", "solutions engineer"]),
    ("engineering", ["software engineer", "backend", "frontend", "full stack", "developer", "engineer"]),
]

# Curated skill vocabulary — only skills found verbatim in the JD are returned (no hallucination).
_SKILL_VOCAB: list[str] = [
    "SQL", "Python", "Java", "JavaScript", "TypeScript", "Go", "Rust", "C++",
    "machine learning", "deep learning", "NLP", "A/B testing", "Tableau", "Power BI",
    "Excel", "roadmapping", "agile", "scrum", "Jira", "Figma", "AWS", "GCP", "Azure",
    "Docker", "Kubernetes", "Spark", "Hadoop", "ETL", "data visualization", "statistics",
    "REST", "GraphQL", "React", "FastAPI", "PostgreSQL", "MongoDB", "Kafka",
]

# Phrases that signal must-have soft requirements when present in the JD.
_KEYWORD_VOCAB: list[str] = [
    "cross-functional", "stakeholder", "leadership", "communication", "strategy",
    "client", "roadmap", "KPIs", "metrics", "collaboration", "ownership",
]

_SENIORITY_SENIOR = ["senior", "lead", "principal", "staff", "head of", "director"]
_SENIORITY_JUNIOR = ["junior", "entry-level", "entry level", "associate", "intern", "graduate"]


class QueryUnderstander:
    """Parse a job description into structured intent before retrieval.

    Uses Ollama when available; falls back to deterministic keyword rules.
    The fallback never invents skills — it returns only terms present in the JD.
    """

    def __init__(self, ollama_client: Any, prompt_loader: Any) -> None:
        self._ollama = ollama_client
        self._loader = prompt_loader

    def understand(self, job_description: str) -> dict:
        if self._ollama and self._ollama.is_available():
            llm = self._llm_understand(job_description)
            if llm is not None:
                return llm
        return self._fallback_understand(job_description)

    # ── LLM path ──────────────────────────────────────────────────────────────

    def _llm_understand(self, job_description: str) -> dict | None:
        try:
            prompt = self._loader.load("intelligence/understand_query")
            user = prompt["user_template"].format(job_description=job_description[:2000])
            raw = self._ollama.generate(
                model=_DEFAULT_MODEL,
                prompt=user,
                temperature=0.0,
                system=prompt["system"],
            )
            data = json.loads(raw)
            # Normalize required fields so callers can rely on the shape.
            return {
                "role_type": data.get("role_type", "engineering"),
                "seniority": data.get("seniority", "mid"),
                "required_skills": list(data.get("required_skills", [])),
                "preferred_skills": list(data.get("preferred_skills", [])),
                "must_have_keywords": list(data.get("must_have_keywords", [])),
            }
        except Exception as exc:
            logger.warning("query_understander: LLM parse failed (%s), using fallback", exc)
            return None

    # ── Deterministic fallback ─────────────────────────────────────────────────

    def _fallback_understand(self, job_description: str) -> dict:
        jd_lower = job_description.lower()
        return {
            "role_type": self._classify_role(jd_lower),
            "seniority": self._detect_seniority(jd_lower),
            "required_skills": self._extract_present(jd_lower, _SKILL_VOCAB),
            "preferred_skills": [],
            "must_have_keywords": self._extract_present(jd_lower, _KEYWORD_VOCAB),
        }

    def _classify_role(self, jd_lower: str) -> str:
        for role_type, signals in _ROLE_SIGNALS:
            if any(sig in jd_lower for sig in signals):
                return role_type
        return "engineering"

    def _detect_seniority(self, jd_lower: str) -> str:
        if any(s in jd_lower for s in _SENIORITY_JUNIOR):
            return "junior"
        if any(s in jd_lower for s in _SENIORITY_SENIOR):
            return "senior"
        return "mid"

    def _extract_present(self, jd_lower: str, vocab: list[str]) -> list[str]:
        """Return vocab terms that appear verbatim in the JD (guarantees non-hallucination)."""
        return [term for term in vocab if term.lower() in jd_lower]
