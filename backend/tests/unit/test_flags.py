"""Phase 18.2 (ADR-020) — feature flags + deterministic A/B."""
from __future__ import annotations

from backend.services import flags


def test_unknown_flag_is_off(test_session):
    assert flags.is_enabled(test_session, "nope") is False


def test_explicit_enable_disable(test_session):
    flags.set_flag(test_session, "beta", enabled=True)
    assert flags.is_enabled(test_session, "beta") is True
    flags.set_flag(test_session, "beta", enabled=False)  # flag-flip rollback
    assert flags.is_enabled(test_session, "beta") is False


def test_rollout_zero_and_one(test_session):
    flags.set_flag(test_session, "f0", rollout=0.0)
    flags.set_flag(test_session, "f1", rollout=1.0)
    assert flags.is_enabled(test_session, "f0", "t1") is False
    assert flags.is_enabled(test_session, "f1", "t1") is True


def test_bucket_is_deterministic_and_offline():
    a = flags.bucket("tenant-x", "feat")
    b = flags.bucket("tenant-x", "feat")
    assert a == b  # reproducible, no server
    assert 0.0 <= a < 1.0
    # Different inputs spread across the range.
    assert flags.bucket("tenant-y", "feat") != a


def test_rollout_buckets_some_in_some_out(test_session):
    flags.set_flag(test_session, "half", rollout=0.5)
    results = [flags.is_enabled(test_session, "half", f"tenant-{i}") for i in range(50)]
    # A 50% rollout should not be all-on or all-off across 50 tenants.
    assert any(results) and not all(results)
