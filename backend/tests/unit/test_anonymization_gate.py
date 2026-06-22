"""Phase 12.15 — the k-anonymity emission gate is the deliverable.

A pattern backed by < k tenants is dropped; a disallowed field is rejected.
"""
from __future__ import annotations

import pytest

from backend.services.flywheel.anonymization import (
    K_ANONYMITY,
    ReidentificationError,
    gate,
)


def _pattern(skill: str, tenant_count: int) -> dict:
    return {
        "pattern_type": "skill_roi", "industry": "technology", "key": skill,
        "value": 0.2, "metric": "interview_lift", "tenant_count": tenant_count,
        "confidence": "strong_inference",
    }


def test_drops_patterns_below_k_tenants():
    assert K_ANONYMITY == 5
    patterns = [_pattern("python", 6), _pattern("rust", 4), _pattern("go", 5)]
    out = gate(patterns)
    keys = {p["key"] for p in out}
    assert keys == {"python", "go"}      # rust (n=4 < 5) suppressed; go (n=5) kept


def test_rejects_disallowed_field():
    bad = _pattern("python", 6)
    bad["tenant_id"] = "t1"              # a per-tenant identifier must never be emitted
    with pytest.raises(ReidentificationError, match="tenant_id"):
        gate([bad])


def test_rejects_raw_text_field():
    bad = _pattern("python", 6)
    bad["raw_text"] = "increased revenue by 40% at Acme"
    with pytest.raises(ReidentificationError):
        gate([bad])


def test_empty_input_is_empty_output():
    assert gate([]) == []
