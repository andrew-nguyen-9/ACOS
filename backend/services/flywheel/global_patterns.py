"""Phase 12.15 cross-tenant pattern + ROI aggregation (ADR-009).

Reads each tenant's ROI (12.11 `rank_skills`, computed from rollups — never raw rows),
aggregates into industry-keyed abstractions, and passes every candidate through the
k-anonymity gate before it can be persisted or returned. Local tenants only; no network.
"""
from __future__ import annotations

from collections import defaultdict

from sqlalchemy.orm import Session

from backend.models.global_pattern import GlobalPattern
from backend.services.flywheel import anonymization
from backend.services.flywheel.skill_roi import rank_skills
from backend.services.tenancy import set_session_tenant


def aggregate_skill_roi(
    session: Session,
    tenant_industries: dict[str, str],
    *,
    metric: str = "interview_lift",
    k: int = anonymization.K_ANONYMITY,
) -> list[dict]:
    """Aggregate per-tenant skill ROI into gated, industry-keyed global patterns.

    ``tenant_industries`` maps each local tenant to its target industry (an abstraction
    about the profile, supplied by the caller — never derived by reading another
    tenant's rows). Returns only k-anonymous, allowlisted patterns.
    """
    rois: dict[tuple[str, str], list[float]] = defaultdict(list)
    tenants: dict[tuple[str, str], set[str]] = defaultdict(set)

    for tenant_id, industry in tenant_industries.items():
        set_session_tenant(session, tenant_id)  # scope reads to this tenant (12.14)
        ranked = rank_skills(session, tenant_id=tenant_id, metric=metric)
        for skill in ranked["skills"]:
            key = (industry, skill["skill"])
            rois[key].append(skill["roi"])
            tenants[key].add(tenant_id)

    candidates: list[dict] = []
    for (industry, skill), values in rois.items():
        tenant_count = len(tenants[(industry, skill)])
        candidates.append({
            "pattern_type": "skill_roi",
            "industry": industry,
            "key": skill,
            "value": round(sum(values) / len(values), 4),
            "metric": metric,
            "tenant_count": tenant_count,
            "confidence": "strong_inference" if tenant_count >= k else "weak_inference",
        })

    # sort for determinism, then gate (drops < k, rejects disallowed fields)
    candidates.sort(key=lambda c: (-c["value"], c["industry"], c["key"]))
    return anonymization.gate(candidates, k=k)


def refresh_global_patterns(
    session: Session,
    tenant_industries: dict[str, str],
    *,
    metric: str = "interview_lift",
) -> int:
    """Recompute and replace the persisted global skill-ROI patterns. Returns the count.

    Off-hot-path batch refresh; reads serve the cached rows.
    """
    patterns = aggregate_skill_roi(session, tenant_industries, metric=metric)
    # replace this metric's skill_roi rows wholesale (idempotent recompute)
    for row in session.query(GlobalPattern).filter(
        GlobalPattern.pattern_type == "skill_roi", GlobalPattern.metric == metric
    ).all():
        session.delete(row)
    for p in patterns:
        session.add(GlobalPattern(
            pattern_type=p["pattern_type"], industry=p["industry"], key=p["key"],
            value=p["value"], metric=p["metric"], tenant_count=p["tenant_count"],
            confidence=p["confidence"],
        ))
    session.flush()
    return len(patterns)


def global_skill_roi(session: Session, *, metric: str = "interview_lift") -> list[dict]:
    """Read the persisted global rankings (aggregate-only, no per-tenant attribution)."""
    rows = session.query(GlobalPattern).filter(
        GlobalPattern.pattern_type == "skill_roi", GlobalPattern.metric == metric
    ).order_by(GlobalPattern.value.desc()).all()
    return [
        {"industry": r.industry, "skill": r.key, "roi": r.value,
         "tenant_count": r.tenant_count, "confidence": r.confidence}
        for r in rows
    ]
