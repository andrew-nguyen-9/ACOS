"""Drift detection over recorded metrics (Phase 11.2).

Reports only — any remediation is an approval-gated suggestion in 11.4. Drift is
a baseline (first window mean) vs current (last window mean) comparison against a
per-kind threshold.

# ponytail: rolling-mean threshold; swap for CUSUM/z-score only if false alarms
# become a problem on real data.
"""
from __future__ import annotations

import math

from sqlalchemy.orm import Session

from backend.models.system_config import SystemConfig
from backend.services.observability.metrics import VALID_KINDS, MetricsStore

# Default absolute drift thresholds per metric kind. Overridable via
# system_config key ``drift_threshold::<kind>``.
_DEFAULT_THRESHOLDS: dict[str, float] = {
    "retrieval_quality": 0.15,
    "ats_score": 10.0,
    "interview_conversion": 0.15,
    "embedding_drift": 0.2,
    "prompt_perf": 0.15,
}


def _mean(values: list[float]) -> float:
    return sum(values) / len(values)


def _cosine_distance(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0 or nb == 0:
        return 1.0
    return 1.0 - dot / (na * nb)


def compute_embedding_drift(texts, embedder, stored_vectors) -> float:
    """Mean cosine distance between freshly-embedded `texts` and `stored_vectors`.

    A cheap, sampled signal that the embedding space has shifted (e.g. model
    changed). Caller records the result as an ``embedding_drift`` metric.
    """
    dists = [
        _cosine_distance(embedder.embed(t), stored)
        for t, stored in zip(texts, stored_vectors)
    ]
    return _mean(dists) if dists else 0.0


class DriftDetector:
    def __init__(self, session: Session) -> None:
        self._session = session
        self._store = MetricsStore(session)

    def _threshold(self, kind: str) -> float:
        row = self._session.get(SystemConfig, f"drift_threshold::{kind}")
        if row is not None and row.value:
            return float(row.value)
        return _DEFAULT_THRESHOLDS.get(kind, 0.15)

    def report(self, window: int = 5) -> list[dict]:
        out: list[dict] = []
        for kind in sorted(VALID_KINDS):
            values = [m.value for m in self._store.series(kind)]
            threshold = self._threshold(kind)
            if len(values) < 2:
                out.append({
                    "kind": kind,
                    "baseline": None,
                    "current": None,
                    "delta": None,
                    "threshold": threshold,
                    "drifting": False,
                    "samples": len(values),
                })
                continue
            baseline = _mean(values[:window])
            current = _mean(values[-window:])
            delta = current - baseline
            out.append({
                "kind": kind,
                "baseline": round(baseline, 6),
                "current": round(current, 6),
                "delta": round(delta, 6),
                "threshold": threshold,
                "drifting": abs(delta) > threshold,
                "samples": len(values),
            })
        return out
