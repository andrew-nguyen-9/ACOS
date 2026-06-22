"""Success anchoring (Phase 11.3).

Picks high-performing resume strategies (templates) by aggregate success and
exposes them as anchors. Anchors are scored by *mean* success weight per
template — a recency-agnostic measure — so a flood of recent low-success
applications on other templates cannot dilute or evict a prior winner.

The selector/outcome_learner *adds* anchors to the candidate set before ranking
(never pins them to output); ranking still decides. Anchor count is capped.
"""
from __future__ import annotations

import math
from collections import defaultdict

from sqlalchemy.orm import Session

DEFAULT_PERCENTILE = 0.75
DEFAULT_MAX_COUNT = 3


def _percentile(values: list[float], p: float) -> float:
    """Linear-interpolation percentile (numpy-free to stay off the import path)."""
    if not values:
        return 0.0
    s = sorted(values)
    k = (len(s) - 1) * p
    f = math.floor(k)
    c = math.ceil(k)
    if f == c:
        return s[int(k)]
    return s[f] * (c - k) + s[c] * (k - f)


def _load_config(session: Session) -> tuple[float, int]:
    from backend.repositories.system_config import SystemConfigRepository

    try:
        repo = SystemConfigRepository(session)
        pct = repo.get_value("anchor_percentile")
        cap = repo.get_value("anchor_max_count")
        return (
            float(pct) if pct else DEFAULT_PERCENTILE,
            int(cap) if cap else DEFAULT_MAX_COUNT,
        )
    except (TypeError, ValueError):
        # Malformed/unavailable config → fall back to defaults rather than crash.
        return DEFAULT_PERCENTILE, DEFAULT_MAX_COUNT


def select_anchors(
    session: Session,
    top_n: int | None = None,
    percentile: float | None = None,
) -> list[dict]:
    """Return high-success template anchors, sorted desc, capped at top_n.

    Each anchor: {"template_name", "success_score", "signal_count"}.
    """
    from backend.repositories.outcome import OutcomeSignalRepository

    cfg_pct, cfg_cap = _load_config(session)
    percentile = cfg_pct if percentile is None else percentile
    top_n = cfg_cap if top_n is None else top_n

    # ponytail: loads all signals (personal-scale: hundreds over years). Swap to
    # SELECT template_used, AVG(signal_weight), COUNT(*) GROUP BY if it ever grows.
    weights_by_template: dict[str, list[float]] = defaultdict(list)
    for s in OutcomeSignalRepository(session).list():
        if s.template_used:
            weights_by_template[s.template_used].append(s.signal_weight)

    scores = {
        tmpl: sum(ws) / len(ws) for tmpl, ws in weights_by_template.items()
    }
    if not scores:
        return []

    cutoff = _percentile(list(scores.values()), percentile)
    anchors = [
        {
            "template_name": tmpl,
            "success_score": round(score, 4),
            "signal_count": len(weights_by_template[tmpl]),
        }
        for tmpl, score in scores.items()
        if score >= cutoff and score > 0.0
    ]
    anchors.sort(key=lambda a: a["success_score"], reverse=True)
    return anchors[:top_n]
