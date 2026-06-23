"""Phase 14.2 — drift helpers: resume success rate + ADR-006 confidence band.

Pure logic, no DB. The success-rate definition and the low-n confidence band are
the only genuinely new computation; ATS-score and embedding-drift series already
exist (Phase 11.2). Descriptive only (no forecasting — ponytail rung 1).
"""
from __future__ import annotations

from backend.services.observability.drift import drift_confidence, resume_success_rate


def test_success_rate_counts_progress_past_rejection():
    # interview + offer are progress; rejected + no_response are not → 2/4
    assert resume_success_rate(["interview", "offer", "rejected", "no_response"]) == 0.5


def test_success_rate_all_negative_is_zero():
    assert resume_success_rate(["rejected", "no_response"]) == 0.0


def test_success_rate_empty_is_none():
    # No data → no fabricated rate (ADR-006).
    assert resume_success_rate([]) is None


def test_confidence_band_adr006():
    assert drift_confidence(0) is None       # dormant — nothing to show
    assert drift_confidence(1) is None       # 1 sample can't drift
    assert drift_confidence(4) == "weak_inference"
    assert drift_confidence(10) == "strong_inference"
    assert drift_confidence(20) == "verified"
