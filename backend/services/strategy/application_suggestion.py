"""15.2 — Application Suggestion Engine (Apply / Skip / Tailor).

Composes the existing Phase-9 engines into one per-application recommendation —
it does NOT rebuild any scoring. Recommend-only (ADR-012): there is no outbound
action path here; the surface produces information the user acts on.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from backend.services.cover_letter.generator import tone_descriptor
from backend.services.strategy.application_strategy import ApplicationStrategyEngine
from backend.services.strategy.career_path_simulator import CareerPathSimulator
from backend.services.strategy.resume_strategy_selector import (
    ResumeStrategySelector,
    _detect_category,
)

# Map the strategy engine's priority to a user-facing recommendation. Trap 2:
# Tailor-First is the safe default — only an outright high-fit match says "apply";
# moderate/bridgeable fit says "tailor", never over-encouraging an application.
_RECOMMENDATION = {
    "prioritize": "apply",
    "tailor": "tailor",
    "bridge": "tailor",
    "skip": "skip",
}


class ApplicationSuggestionEngine:
    def __init__(self, session: Session) -> None:
        self._session = session
        self._strategy = ApplicationStrategyEngine(session)
        self._resume = ResumeStrategySelector(session)
        self._career = CareerPathSimulator(session)

    def suggest(self, jd_text: str) -> dict:
        # Reuse the enriched, server-ranked prioritize row (carries confidence +
        # evidence already) — single source of truth for the fit decision.
        row = self._strategy.prioritize([{"job_id": "_", "jd_text": jd_text}])[0]
        recommendation = _RECOMMENDATION[row["priority"]]
        resume = self._resume.recommend(jd_text)
        interview = self._interview_outlook(jd_text)
        tone, descriptor = self._cl_tone(recommendation)
        return {
            "recommendation": recommendation,
            "reason": row["reason"],
            "fit_score": row["fit_score"],
            "confidence": row["confidence"],
            "missing_critical_skills": row["missing_critical_skills"],
            "risk_factors": row["risk_factors"],
            "explanation": row["explanation"],
            "resume_template": resume["template_name"],
            "resume_reason": resume["reason"],
            "cover_letter_tone": tone,
            "cover_letter_tone_descriptor": descriptor,
            "interview_probability": interview["interview_probability"],
            "interview_sample_size": interview["sample_size"],
            "interview_confidence": interview["confidence"],
            "interview_category": interview["category"],
        }

    def _interview_outlook(self, jd_text: str) -> dict:
        category = _detect_category(jd_text)
        for path in self._career.simulate_all():
            if path["category"] == category:
                return path
        # simulate_all yields every category; this fallback is defensive only.
        return {
            "category": category,
            "interview_probability": 0.0,
            "sample_size": 0,
            "confidence": "weak_inference",
        }

    def _cl_tone(self, recommendation: str) -> tuple[float, str]:
        # ponytail: a strong recommendation → a bolder letter; otherwise balanced.
        # The 0..1 dial + descriptor band is the 11.9 RCL-003 contract.
        tone = 0.66 if recommendation == "apply" else 0.5
        return tone, tone_descriptor(tone)
