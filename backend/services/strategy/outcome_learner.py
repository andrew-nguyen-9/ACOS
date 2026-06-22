"""U7 — Historical Outcome Learning / Analytics.

Aggregates OutcomeSignals into:
  - category_breakdown: interview/offer rates per career category
  - ats_threshold: outcome rate by ATS score bucket
"""
from __future__ import annotations

import logging
from collections import defaultdict
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from backend.repositories.outcome import OutcomeSignalRepository
from backend.services.learning import retention
from backend.services.strategy.career_path_simulator import _match_category

logger = logging.getLogger(__name__)

_ATS_BUCKETS = ["0-20", "20-40", "40-60", "60-80", "80-100"]


def _age_days(created_at: object) -> float:
    """Days since created_at (ISO string); 0.0 if missing/unparseable."""
    if not isinstance(created_at, str):
        return 0.0
    try:
        ts = datetime.fromisoformat(created_at)
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        return max(0.0, (datetime.now(timezone.utc) - ts).total_seconds() / 86400.0)
    except ValueError:
        return 0.0


def _bucket_label(score: float) -> str:
    if score < 20:
        return "0-20"
    if score < 40:
        return "20-40"
    if score < 60:
        return "40-60"
    if score < 80:
        return "60-80"
    return "80-100"


class OutcomeLearner:
    def __init__(self, session: Session) -> None:
        self._session = session

    def outcome_report(self) -> dict:
        repo = OutcomeSignalRepository(self._session)
        signals = repo.list()
        # Tunable retention knob (system_config); falls back to module defaults.
        floor_fraction, tau_days = retention.load_constants(self._session)

        # Category breakdown
        cat_signals: dict[str, list] = defaultdict(list)
        for s in signals:
            cat = _match_category(s.position_type)
            if cat:
                cat_signals[cat].append(s)

        category_breakdown = []
        for cat, sigs in cat_signals.items():
            n = len(sigs)
            interview_rate = round(sum(1 for s in sigs if s.signal_weight > 0.3) / n, 3) if n else 0.0
            offer_rate = round(sum(1 for s in sigs if s.signal_weight >= 0.85) / n, 3) if n else 0.0
            avg_weight = round(sum(s.signal_weight for s in sigs) / n, 3) if n else 0.0
            # Retention weighting: recency-decayed success with a permanent floor,
            # so old winners never vanish and recent results weigh full.
            weighted = (
                round(
                    sum(
                        retention.weight(
                            s.signal_weight,
                            _age_days(s.created_at),
                            floor_fraction=floor_fraction,
                            tau_days=tau_days,
                        )
                        for s in sigs
                    )
                    / n,
                    3,
                )
                if n
                else 0.0
            )
            confidence = "verified" if n >= 10 else "strong_inference" if n >= 3 else "weak_inference"
            category_breakdown.append(
                {
                    "category": cat,
                    "total": n,
                    "interview_rate": interview_rate,
                    "offer_rate": offer_rate,
                    "avg_signal_weight": avg_weight,
                    "weighted_signal": weighted,
                    "confidence": confidence,
                }
            )
        category_breakdown.sort(key=lambda r: r["interview_rate"], reverse=True)

        # ATS threshold buckets
        ats_signals = [s for s in signals if s.ats_score is not None]
        buckets: dict[str, list[float]] = defaultdict(list)
        for s in ats_signals:
            buckets[_bucket_label(s.ats_score)].append(s.signal_weight)

        ats_threshold = [
            {
                "range": label,
                "outcome_rate": round(sum(w) / len(w), 3) if w else 0.0,
                "count": len(w),
            }
            for label, w in [(b, buckets[b]) for b in _ATS_BUCKETS]
        ]

        return {
            "category_breakdown": category_breakdown,
            "ats_threshold": ats_threshold,
            "total_signals": len(signals),
        }
