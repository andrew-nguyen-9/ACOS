"""U3 — Career Path Simulator.

For each of the 6 career categories, computes interview/offer probability
from historical OutcomeSignals filtered by position_type keyword matching.
"""
from __future__ import annotations

import logging
from collections import defaultdict

from sqlalchemy.orm import Session

from backend.repositories.outcome import OutcomeSignalRepository

logger = logging.getLogger(__name__)

CATEGORY_KEYWORDS: dict[str, list[str]] = {
    "product_management": ["product", "roadmap", "stakeholder", "user research", "okr", "prd", "sprint", "product manager"],
    "data_analytics": ["analytics", "sql", "python", "dashboard", "etl", "tableau", "pipeline", "data analyst", "data science"],
    "litigation_consulting": ["litigation", "legal", "expert", "damages", "discovery", "ediscovery", "forensic"],
    "ai_ml": ["machine learning", "llm", "nlp", "model", "ai", "deep learning", "mlops", "data scientist"],
    "consulting": ["strategy", "client", "workstream", "engagement", "advisory", "management consulting"],
    "tpm_solutions": ["tpm", "solutions engineer", "implementation", "integration", "customer success", "technical program"],
}


def _match_category(position_type: str | None) -> str | None:
    if not position_type:
        return None
    pt = position_type.lower()
    best: str | None = None
    best_count = 0
    for cat, keywords in CATEGORY_KEYWORDS.items():
        count = sum(1 for kw in keywords if kw in pt)
        if count > best_count:
            best_count = count
            best = cat
    return best if best_count > 0 else None


class CareerPathSimulator:
    def __init__(self, session: Session) -> None:
        self._session = session

    def simulate_all(self) -> list[dict]:
        repo = OutcomeSignalRepository(self._session)
        signals = repo.list()

        # bucket signals by category
        by_cat: dict[str, list] = defaultdict(list)
        for s in signals:
            cat = _match_category(s.position_type)
            if cat:
                by_cat[cat].append(s)

        results = []
        for cat in CATEGORY_KEYWORDS:
            cat_signals = by_cat.get(cat, [])
            results.append(self._compute(cat, cat_signals))
        results.sort(key=lambda r: r["interview_probability"], reverse=True)
        return results

    def _compute(self, category: str, signals: list) -> dict:
        n = len(signals)
        if n == 0:
            return {
                "category": category,
                "interview_probability": 0.0,
                "offer_probability": 0.0,
                "expected_timeline_days": None,
                "difficulty_rating": 1.0,
                "sample_size": 0,
                "confidence": "weak_inference",
            }

        interview_prob = round(
            sum(1 for s in signals if s.signal_weight > 0.3) / n, 3
        )
        offer_prob = round(
            sum(1 for s in signals if s.signal_weight >= 0.85) / n, 3
        )
        difficulty = round(1.0 - interview_prob, 3)
        confidence = "verified" if n >= 10 else "strong_inference" if n >= 3 else "weak_inference"

        return {
            "category": category,
            "interview_probability": interview_prob,
            "offer_probability": offer_prob,
            "expected_timeline_days": None,  # future: parse application → outcome date delta
            "difficulty_rating": difficulty,
            "sample_size": n,
            "confidence": confidence,
        }
