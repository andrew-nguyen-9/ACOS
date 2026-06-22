"""Weighted historical memory retention (Phase 11.3).

weight(success, age) = success * max(floor_fraction, recency_factor(age))
- recency_factor is a gentle exponential decay in age_days.
- floor_fraction guarantees proven-but-old winners keep a permanent base weight,
  so they never decay to zero (eviction resistance).
"""
from __future__ import annotations

import math

from backend.services.learning import retention


def test_age_zero_gives_full_success_score():
    assert retention.weight(0.9, 0.0) == 0.9


def test_recency_decays_weight():
    fresh = retention.weight(0.9, 0.0)
    old = retention.weight(0.9, 365.0)
    assert old < fresh


def test_monotonic_non_increasing_in_age():
    w = [retention.weight(0.8, a) for a in (0, 30, 90, 180, 365, 1000)]
    assert all(earlier >= later for earlier, later in zip(w, w[1:]))


def test_floor_prevents_zero_for_high_success():
    # Even at extreme age, a high-success item keeps its floor weight.
    w = retention.weight(0.9, 100_000.0, floor_fraction=0.25)
    assert math.isclose(w, 0.25 * 0.9, rel_tol=1e-9)
    assert w > 0


def test_zero_success_has_zero_weight():
    assert retention.weight(0.0, 0.0) == 0.0
    assert retention.weight(0.0, 1000.0) == 0.0


def test_higher_success_outranks_at_equal_age():
    assert retention.weight(0.9, 200.0) > retention.weight(0.4, 200.0)


def test_high_success_old_can_outrank_low_success_fresh():
    # The anchoring guarantee at the weight level: a strong old winner beats a
    # weak fresh item once the floor kicks in.
    old_winner = retention.weight(0.95, 100_000.0, floor_fraction=0.25)
    fresh_weak = retention.weight(0.10, 0.0)
    assert old_winner > fresh_weak


def test_constants_loaded_from_config(test_session):
    from backend.database import seed_system_config

    seed_system_config(test_session)
    floor, tau = retention.load_constants(test_session)
    assert 0.0 < floor < 1.0
    assert tau > 0
