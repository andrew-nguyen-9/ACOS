from __future__ import annotations

import logging
from collections import defaultdict

from sqlalchemy.orm import Session

from backend.repositories.outcome import OutcomeSignalRepository

logger = logging.getLogger(__name__)

_SIGNAL_WEIGHTS: dict[str, float] = {
    "no_response": 0.0,
    "rejected": 0.1,
    "phone_screen": 0.4,
    "interview": 0.7,
    "final_round": 0.85,
    "offer": 1.0,
    "accepted": 1.0,
}

_VALID_SIGNALS = set(_SIGNAL_WEIGHTS.keys())


class OutcomeRanker:
    def __init__(self, session: Session) -> None:
        self._session = session

    def record_outcome(
        self,
        application_id: str,
        signal_type: str,
        resume_id: str | None = None,
        template_used: str | None = None,
        ats_score: float | None = None,
        industry: str | None = None,
        position_type: str | None = None,
    ) -> dict:
        if signal_type not in _VALID_SIGNALS:
            raise ValueError(
                f"Invalid signal_type '{signal_type}'. Must be one of {sorted(_VALID_SIGNALS)}"
            )
        repo = OutcomeSignalRepository(self._session)
        weight = _SIGNAL_WEIGHTS[signal_type]
        signal = repo.create(
            application_id=application_id,
            signal_type=signal_type,
            signal_weight=weight,
            resume_id=resume_id,
            template_used=template_used,
            ats_score=ats_score,
            industry=industry,
            position_type=position_type,
        )
        # 12.10 flywheel emit: normalize this outcome into a source-linked signal.
        # Best-effort — a feedback-loop hiccup must never fail outcome recording.
        try:
            from backend.services.flywheel.feedback import record_signal

            record_signal(
                self._session,
                entity_type="application",
                entity_id=application_id,
                signal_type=signal_type,
                value=weight,
                source={"table": "outcome_signals", "ids": [signal.id]},
            )
        except Exception:  # noqa: BLE001 — telemetry never breaks the write path
            logger.warning("flywheel signal emit failed for outcome %s", signal.id, exc_info=True)
        return {
            "signal_id": signal.id,
            "signal_type": signal.signal_type,
            "signal_weight": signal.signal_weight,
            "application_id": signal.application_id,
        }

    def get_template_rankings(self) -> list[dict]:
        repo = OutcomeSignalRepository(self._session)
        signals = repo.list()
        by_template: dict[str, list[float]] = defaultdict(list)
        signal_types_map: dict[str, list[str]] = defaultdict(list)
        for s in signals:
            key = s.template_used or "unknown"
            by_template[key].append(s.signal_weight)
            signal_types_map[key].append(s.signal_type)
        rankings = [
            {
                "template_name": template,
                "score": round(sum(weights) / len(weights), 4),
                "signal_count": len(weights),
                "signal_types": list(set(signal_types_map[template])),
            }
            for template, weights in by_template.items()
        ]
        rankings.sort(key=lambda r: r["score"], reverse=True)
        return rankings

    def get_ats_vs_outcome_correlation(self) -> dict:
        repo = OutcomeSignalRepository(self._session)
        signals = [s for s in repo.list() if s.ats_score is not None]
        buckets: dict[str, list[float]] = {
            "0-20": [], "20-40": [], "40-60": [], "60-80": [], "80-100": [],
        }
        for s in signals:
            score = s.ats_score
            if score < 20:
                buckets["0-20"].append(s.signal_weight)
            elif score < 40:
                buckets["20-40"].append(s.signal_weight)
            elif score < 60:
                buckets["40-60"].append(s.signal_weight)
            elif score < 80:
                buckets["60-80"].append(s.signal_weight)
            else:
                buckets["80-100"].append(s.signal_weight)
        result = [
            {
                "range": range_label,
                "outcome_rate": (
                    round(sum(weights) / len(weights), 4) if weights else 0.0
                ),
                "count": len(weights),
            }
            for range_label, weights in buckets.items()
        ]
        return {"buckets": result, "total_signals": len(signals)}
