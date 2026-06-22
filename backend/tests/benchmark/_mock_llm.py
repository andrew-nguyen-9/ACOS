"""Deterministic LLM doubles for perf benches.

Benches measure *our* orchestration overhead, not Ollama. The mock returns a
fixed response immediately (optional `latency_s` can emulate model latency, but
default 0 keeps the signal on our code). See plan §10 — real-model latency is
tracked separately in 11.3 with live Ollama.
"""
from __future__ import annotations

import json
import time
from unittest.mock import MagicMock

from backend.services.copilot.engine import CopilotEngine
from backend.services.resume.generator import ResumeGenerator

_RESUME_JSON = json.dumps(
    {
        "experiences": [
            {
                "title": "Data Engineer",
                "company": "Acme Corp",
                "dates": "2022–2024",
                "bullets": [
                    {
                        "text": "Built Python ETL pipeline reducing processing time by 40%",
                        "evidence_id": "b1",
                        "confidence": "verified",
                    }
                ],
            }
        ],
        "skills": ["Python", "ETL", "SQL"],
        "projects": [],
        "education": [],
    }
)


class FixedLatencyLLM:
    """Ollama stand-in returning a constant response.

    `latency_s` emulates model think-time; default 0 so the bench reflects our
    own code path rather than a sleep.
    """

    def __init__(self, response: str = _RESUME_JSON, latency_s: float = 0.0) -> None:
        self._response = response
        self._latency_s = latency_s

    def is_available(self) -> bool:
        return True

    def generate(self, *args: object, **kwargs: object) -> str:
        if self._latency_s:
            time.sleep(self._latency_s)
        return self._response

    def embed(self, *args: object, **kwargs: object) -> list[float]:
        return [0.0] * 768


def build_resume_generator(session) -> ResumeGenerator:
    """ResumeGenerator wired with deterministic mocks + a fixed-latency LLM."""
    selector = MagicMock()
    selector.select.return_value = [
        {
            "bullet_text": "Built Python ETL pipeline reducing processing time by 40%",
            "evidence_id": "b1",
            "experience_id": "exp1",
            "company": "Acme Corp",
            "title": "Data Engineer",
            "dates": "2022-01–2024-01",
            "confidence": "verified",
        }
    ]

    kw_extractor = MagicMock()
    kw_extractor.extract.return_value = {
        "required_skills": ["Python", "ETL"],
        "preferred_skills": [],
        "keywords": ["data pipeline", "Python"],
        "industry": "technology",
        "seniority_level": "senior",
    }

    ats_scorer = MagicMock()
    ats_scorer.score.return_value = {
        "overall_score": 85,
        "keyword_score": 88,
        "skill_score": 82,
        "experience_score": 80,
        "industry_score": 90,
        "matched_keywords": ["Python", "ETL"],
        "missing_keywords": [],
        "explanation": "Strong match.",
    }

    loader = MagicMock()
    loader.load.return_value = {
        "version": "1.0",
        "system": "Generate resume",
        "user_template": "JD: {job_description}\nTemplate: {template_name}\n"
        "Keywords: {keywords}\nEvidence: {evidence_json}",
    }

    return ResumeGenerator(
        selector, kw_extractor, ats_scorer, FixedLatencyLLM(), loader, session
    )


def build_copilot_engine() -> CopilotEngine:
    """CopilotEngine with a deterministic RAG double (no Chroma, no Ollama)."""
    rag = MagicMock()
    rag.query.return_value = {
        "response": "Here is tailored guidance for your resume.",
        "confidence_summary": "strong_inference",
        "evidence": [
            {
                "source": "experience-bank.md",
                "text": "Built Python ETL pipeline reducing processing time by 40%",
                "confidence": "verified",
                "similarity_score": 0.91,
            }
        ],
    }
    return CopilotEngine(rag)
