"""Weighted historical memory retention (Phase 11.3).

Outcomes/strategies are weighted by recency *and* success. A decay floor keeps
proven-but-old winners from ever dropping to zero, so a flood of recent
low-success items can't evict a prior high-success anchor.

    weight = success_score * max(floor_fraction, recency_factor(age_days))
    recency_factor(age_days) = exp(-age_days / tau_days)   # gentle exponential

Constants live in system_config (tunable — leave the knob):
    retention_floor_fraction, retention_decay_days
"""
from __future__ import annotations

import math

from sqlalchemy.orm import Session

DEFAULT_FLOOR_FRACTION = 0.25
DEFAULT_DECAY_DAYS = 180.0


def recency_factor(age_days: float, tau_days: float = DEFAULT_DECAY_DAYS) -> float:
    return math.exp(-max(0.0, age_days) / tau_days)


def weight(
    success_score: float,
    age_days: float,
    *,
    floor_fraction: float = DEFAULT_FLOOR_FRACTION,
    tau_days: float = DEFAULT_DECAY_DAYS,
) -> float:
    """Recency-decayed success weight with a permanent floor of floor_fraction."""
    return success_score * max(floor_fraction, recency_factor(age_days, tau_days))


def load_constants(session: Session) -> tuple[float, float]:
    """Read (floor_fraction, decay_days) from system_config, with defaults."""
    from backend.repositories.system_config import SystemConfigRepository

    try:
        repo = SystemConfigRepository(session)
        floor = repo.get_value("retention_floor_fraction")
        decay = repo.get_value("retention_decay_days")
        return (
            float(floor) if floor else DEFAULT_FLOOR_FRACTION,
            float(decay) if decay else DEFAULT_DECAY_DAYS,
        )
    except (TypeError, ValueError):
        # Config unavailable/unparseable (e.g. no session) → fall back to defaults.
        return DEFAULT_FLOOR_FRACTION, DEFAULT_DECAY_DAYS
