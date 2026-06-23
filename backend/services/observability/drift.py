"""Drift detection over recorded metrics (Phase 11.2).

Reports only — any remediation is an approval-gated suggestion in 11.4. Drift is
a baseline (first window mean) vs current (last window mean) comparison against a
per-kind threshold.

# ponytail: rolling-mean threshold; swap for CUSUM/z-score only if false alarms
# become a problem on real data.
"""
from __future__ import annotations

import math

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models.outcome import OutcomeSignal
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
    "success_rate": 0.15,
}

# 14.2: an application "succeeded" once it progressed past a rejection / silence.
# A response (phone screen onward) is the signal the resume cleared the first gate.
_POSITIVE_OUTCOMES = {"phone_screen", "interview", "final_round", "offer", "accepted"}


def resume_success_rate(signal_types: list[str]) -> float | None:
    """Fraction of outcomes that progressed past rejection / no-response.

    Returns None on no data — a rate with no denominator is fabricated (ADR-006).
    """
    if not signal_types:
        return None
    positive = sum(1 for s in signal_types if s in _POSITIVE_OUTCOMES)
    return positive / len(signal_types)


def drift_confidence(samples: int) -> str | None:
    """ADR-006 confidence band for a drift figure, by sample count.

    0–1 samples → None (dormant; can't drift). Thin data is de-emphasized, never
    presented as a confident number.
    """
    if samples < 2:
        return None
    if samples < 5:
        return "weak_inference"
    if samples < 15:
        return "strong_inference"
    return "verified"


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
            samples = self._store.series(kind)
            values = [m.value for m in samples]
            threshold = self._threshold(kind)
            # baseline is versioned (14.1): which build produced the first sample
            # this is drifting *from*. Best-effort from the sample's meta.
            baseline_version = samples[0].meta_json.get("app_version") if samples else None
            if len(values) < 2:
                out.append({
                    "kind": kind,
                    "baseline": None,
                    "current": None,
                    "delta": None,
                    "threshold": threshold,
                    "drifting": False,
                    "samples": len(values),
                    "confidence": drift_confidence(len(values)),
                    "baseline_version": baseline_version,
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
                "confidence": drift_confidence(len(values)),
                "baseline_version": baseline_version,
            })
        return out


class DriftSnapshot:
    """Off-hot-path recorder: take a versioned drift sample from current data.

    Triggered by an explicit endpoint (like the 13.6 evolution loop), never per
    request. Records the resume success rate now; ats_score / embedding_drift are
    already sampled at their own events.

    # ponytail: single-tenant local app (ADR-008) — counts all outcomes rather
    # than tenant-filtering; add a tenant filter if a shared deploy ever lands.
    """

    def __init__(self, session: Session) -> None:
        self._session = session
        self._store = MetricsStore(session)

    def record(self, app_version: str) -> dict:
        signal_types = list(
            self._session.scalars(select(OutcomeSignal.signal_type)).all()
        )
        rate = resume_success_rate(signal_types)
        recorded: list[str] = []
        if rate is not None:
            self._store.record("success_rate", rate, {"app_version": app_version})
            recorded.append("success_rate")
        return {"recorded": recorded, "success_rate": rate, "outcomes": len(signal_types)}
