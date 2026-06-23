"""Phase 18.3 — local-only aggregate telemetry.

Descriptive rollups over EXISTING signals: perf summaries (Metric), feature-usage
counts (AuditLog op types), and anonymized success rates (outcome signals). Counts
and rates only — never record bodies or PII (ADR-016 digest precedent). Nothing
leaves the machine: this is a pure local DB read with no network (the only outbound
channel is the ADR-011 update check, which is data-free).

Off-hot-path: computed on demand / on the existing 13.6/14.2 scheduler seam, never
per request.
"""
from __future__ import annotations

from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.models.audit import AuditLog
from backend.models.metric import Metric
from backend.models.outcome import OutcomeSignal

# k-anonymity floor (ADR-009): below this, report a count but suppress the rate so a
# thin sample can't imply a confident, near-identifying number.
_MIN_N = 5

_SUCCESS = {"interview", "offer", "phone_screen", "final_round"}


def local_aggregates(session: Session) -> dict:
    """Aggregate-only telemetry for a local stats surface. No PII, no bodies."""
    # Feature-usage counts — how often each audited operation ran (counts, not content).
    usage_rows = (
        session.query(AuditLog.op_type, func.count(AuditLog.id))
        .group_by(AuditLog.op_type)
        .all()
    )
    usage_counts = {op: int(n) for op, n in usage_rows}

    # Perf summary — mean of each metric kind (numbers, never the meta).
    perf_rows = (
        session.query(Metric.kind, func.avg(Metric.value), func.count(Metric.id))
        .group_by(Metric.kind)
        .all()
    )
    perf = {kind: {"mean": round(float(avg), 3), "n": int(n)} for kind, avg, n in perf_rows}

    # Anonymized success rate from outcome signals; suppressed below the k floor.
    outcomes = session.query(OutcomeSignal).all()
    n = len(outcomes)
    success_rate = None
    if n >= _MIN_N:
        wins = sum(1 for o in outcomes if getattr(o, "signal_type", None) in _SUCCESS)
        success_rate = round(wins / n, 3)

    return {
        "usage_counts": usage_counts,
        "perf": perf,
        "success": {"n": n, "rate": success_rate, "suppressed": n < _MIN_N},
    }
