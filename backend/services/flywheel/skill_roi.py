"""Phase 12.11 Skill ROI Engine.

Read-side compute over the 12.10 ``signals`` table: which skills correlate with
better outcomes, ranked, confidence-aware, explainable, per tenant.

ROI is an *effect size* — the mean outcome of applications that used a skill minus
the global mean — NOT a model (plan §3). Every figure carries ``n`` and a
confidence level (ADR-006): a ROI is inference by construction, so it is
``strong_inference`` once enough applications back it (``n >= min_n``) and
``weak_inference`` below that. ``verified`` never applies — there is no single
source document that "proves" a correlation. Low-n skills are excluded from the
``recommended`` output (Trap 1: a confident ROI on n=1 is the bug).

The skill -> outcome join is free: a ``skill_used`` signal carries the application
id in ``source_json["ids"]``; the outcome signal's ``entity_id`` is that same id.
No new table, no new column.
"""
from __future__ import annotations

from collections import defaultdict

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models.signal import Signal

# Outcome ladder (mirrors learning/ranker weights); ats_score is a separate grain.
_LADDER = {
    "no_response", "rejected", "phone_screen",
    "interview", "final_round", "offer", "accepted",
}
_OFFER = {"offer", "accepted"}
_METRICS = {"interview_lift", "offer_probability", "ats_delta"}


def _metric_value(metric: str, sigs: list[Signal]) -> tuple[float | None, list[str]]:
    """Reduce one application's outcome signals to a single metric scalar.

    Returns ``(value, contributing_outcome_signal_ids)`` or ``(None, [])`` when the
    application has no signal relevant to this metric.
    """
    if metric == "ats_delta":
        ats = [s for s in sigs if s.signal_type == "ats_score"]
        if not ats:
            return None, []
        return sum(s.value for s in ats) / len(ats), [s.id for s in ats]

    ladder = [s for s in sigs if s.signal_type in _LADDER]
    if not ladder:
        return None, []
    if metric == "offer_probability":
        val = 1.0 if any(s.signal_type in _OFFER for s in ladder) else 0.0
        return val, [s.id for s in ladder]
    # interview_lift: the furthest rung the application reached.
    return max(s.value for s in ladder), [s.id for s in ladder]


def rank_skills(
    session: Session,
    tenant_id: str | None = None,
    metric: str = "interview_lift",
    min_n: int = 5,
) -> dict:
    """Rank a tenant's skills by ROI for ``metric``, with n + confidence + sources.

    ``tenant_id=None`` reads all rows (single-tenant world until 12.14).
    """
    if metric not in _METRICS:
        raise ValueError(f"unknown metric '{metric}'; choose from {sorted(_METRICS)}")

    stmt = select(Signal)
    if tenant_id is not None:
        stmt = stmt.where(Signal.tenant_id == tenant_id)
    rows = session.scalars(stmt).all()

    outcomes_by_app: dict[str, list[Signal]] = defaultdict(list)
    skill_uses: list[Signal] = []
    for s in rows:
        if s.entity_type == "application":
            outcomes_by_app[s.entity_id].append(s)
        elif s.entity_type == "skill" and s.signal_type == "skill_used":
            skill_uses.append(s)

    # Per-application metric value + the outcome signal ids that justify it.
    app_value: dict[str, float] = {}
    app_sids: dict[str, list[str]] = {}
    for app_id, sigs in outcomes_by_app.items():
        val, sids = _metric_value(metric, sigs)
        if val is not None:
            app_value[app_id] = val
            app_sids[app_id] = sids

    empty = {"metric": metric, "min_n": min_n, "skills": [], "recommended": []}
    if not app_value:
        return empty

    global_mean = sum(app_value.values()) / len(app_value)

    # skill -> {application_id: skill_used signal id} for applications with a value.
    skill_apps: dict[str, dict[str, str]] = defaultdict(dict)
    for s in skill_uses:
        ids = s.source_json.get("ids", []) if isinstance(s.source_json, dict) else []
        for app_id in ids:
            if app_id in app_value and app_id not in skill_apps[s.entity_id]:
                skill_apps[s.entity_id][app_id] = s.id

    skills: list[dict] = []
    for skill in sorted(skill_apps):
        apps = skill_apps[skill]
        n = len(apps)  # always >= 1: an entry exists only once a valued app is added
        skill_mean = sum(app_value[a] for a in apps) / n
        contributing: list[str] = []
        for app_id in sorted(apps):
            contributing.append(apps[app_id])     # the skill_used signal
            contributing.extend(app_sids[app_id])  # its outcome signal(s)
        skills.append({
            "skill": skill,
            "roi": round(skill_mean - global_mean, 4),
            "n": n,
            "confidence": "strong_inference" if n >= min_n else "weak_inference",
            "contributing_signal_ids": contributing,
        })

    skills.sort(key=lambda s: (-s["roi"], s["skill"]))  # roi desc, stable tie-break
    recommended = [
        s["skill"] for s in skills
        if s["confidence"] == "strong_inference" and s["roi"] > 0
    ]
    return {"metric": metric, "min_n": min_n, "skills": skills, "recommended": recommended}
