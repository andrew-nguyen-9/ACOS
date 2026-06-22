"""Append-only metrics store (Phase 11.2).

Thin layer over the ``metrics`` table: record samples and read them back as a
time series or rolling mean. Drift detection (drift.py) builds on these.
"""
from __future__ import annotations

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from backend.models.metric import Metric

VALID_KINDS = {
    "retrieval_quality",
    "ats_score",
    "interview_conversion",
    "embedding_drift",
    "prompt_perf",
}


class MetricsStore:
    def __init__(self, session: Session) -> None:
        self._session = session

    def record(self, kind: str, value: float, meta: dict | None = None) -> Metric:
        if kind not in VALID_KINDS:
            raise ValueError(f"Unknown metric kind: {kind!r}")
        row = Metric(kind=kind, value=float(value), meta_json=meta or {})
        self._session.add(row)
        self._session.flush()
        return row

    def series(self, kind: str, since: str | None = None) -> list[Metric]:
        stmt = select(Metric).where(Metric.kind == kind)
        if since is not None:
            stmt = stmt.where(Metric.created_at >= since)
        # rowid is SQLite's monotonic insertion order — a stable tiebreaker when
        # created_at timestamps collide within the same microsecond.
        # ponytail: SQLite-specific; the app is SQLite-locked (ADR-002).
        stmt = stmt.order_by(Metric.created_at.asc(), text("rowid"))
        return list(self._session.scalars(stmt).all())

    def rolling(self, kind: str, window: int) -> float | None:
        values = [m.value for m in self.series(kind)]
        if not values:
            return None
        recent = values[-window:]
        return sum(recent) / len(recent)
