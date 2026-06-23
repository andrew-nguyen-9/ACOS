"""Phase 12.15 — no global artifact may contain raw text, embeddings, or tenant ids."""
from __future__ import annotations

import pytest

from backend.services.flywheel.anonymization import (
    ReidentificationError,
    assert_no_reidentification,
)


def test_clean_aggregate_passes():
    artifact = [
        {"pattern_type": "skill_roi", "industry": "technology", "key": "python",
         "value": 0.2, "tenant_count": 6, "confidence": "strong_inference"},
    ]
    assert_no_reidentification(artifact)  # no raise


def test_tenant_id_key_is_caught():
    with pytest.raises(ReidentificationError):
        assert_no_reidentification([{"key": "python", "tenant_id": "t1"}])


def test_embedding_value_is_caught():
    """A list of floats is an embedding — must never appear in a global artifact."""
    with pytest.raises(ReidentificationError):
        assert_no_reidentification([{"key": "python", "value": [0.1, 0.2, 0.3, 0.4]}])


def test_nested_tenant_reference_is_caught():
    with pytest.raises(ReidentificationError):
        assert_no_reidentification({"patterns": [{"key": "x", "tenant": "t2"}]})
