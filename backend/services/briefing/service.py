"""15.4 — Daily Career Briefing orchestrator.

Composes five sections — jobs to apply to, skill gaps, resume adjustments, ATS
opportunities, follow-ups due — from the EXISTING engines, each recommendation
aligned to the tracked career goal. It writes no new ranking/scoring; it is a
read rollup. Recommend-only (ADR-012): it suggests, it never acts.

Off the hot path: this is computed on demand / on a schedule (the explicit-trigger
seam of 13.6, no new scheduler) and is never imported into a generation request,
so it adds zero per-request latency (asserted in test_briefing_off_hot_path).
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from backend.repositories.application import ApplicationRepository
from backend.services.strategy.application_strategy import ApplicationStrategyEngine
from backend.services.strategy.career_path_simulator import CareerPathSimulator
from backend.services.strategy.resume_strategy_selector import (
    ResumeStrategySelector,
    _detect_category,
)
from backend.services.strategy.skill_gap_forecaster import SkillGapForecaster

# Statuses that mean an application is live and may need a nudge.
_ACTIVE_STATUSES = {"applied", "phone_screen", "interview", "final_round"}
# A composed recommendation maps the strategy priority to a user-facing verb.
_REC = {"prioritize": "apply", "tailor": "tailor"}


class BriefingService:
    def __init__(self, session: Session) -> None:
        self._session = session
        self._apps = ApplicationRepository(session)

    def compose(self, max_items: int = 5) -> dict:
        apps = self._apps.list()
        goal = self._goal()
        jobs = self._jobs_to_apply(apps, goal, max_items)
        return {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "goal": goal,
            "jobs_to_apply": jobs,
            "skill_gaps": SkillGapForecaster(self._session).forecast()[:max_items],
            "resume_adjustments": self._resume_adjustments(apps, max_items),
            "ats_opportunities": self._ats_opportunities(apps, max_items),
            "follow_ups": self._follow_ups(apps),
        }

    def _goal(self) -> dict | None:
        """The tracked career goal — the empirically strongest trajectory.

        ponytail: no user-set goal model yet; the goal is the highest-probability
        category the user's own outcome data supports. None when there's no data,
        so the briefing aligns against a real goal or honestly against none.
        """
        paths = CareerPathSimulator(self._session).simulate_all()
        grounded = [p for p in paths if p["sample_size"] > 0]
        return grounded[0] if grounded else None

    def _jobs_to_apply(self, apps: list, goal: dict | None, max_items: int) -> list[dict]:
        jds = [
            {"job_id": a.id, "jd_text": a.job_description}
            for a in apps
            if a.job_description
        ]
        if not jds:
            return []
        rows = ApplicationStrategyEngine(self._session).prioritize(jds)
        by_id = {a.id: a for a in apps}
        out: list[dict] = []
        for r in rows:
            if r["priority"] not in _REC:
                continue  # only surface actionable jobs (apply / tailor)
            app = by_id.get(r["job_id"])
            if app is None:
                continue
            category = _detect_category(app.job_description or "")
            aligned = goal is None or category == goal["category"]
            out.append(
                {
                    "application_id": app.id,
                    "company": app.company,
                    "position": app.position,
                    "recommendation": _REC[r["priority"]],
                    "fit_score": r["fit_score"],
                    "confidence": r["confidence"],
                    "category": category,
                    "aligned_to_goal": aligned,
                }
            )
        # Goal-aligned jobs first (real alignment, not decorative), fit order within.
        out.sort(key=lambda j: not j["aligned_to_goal"])
        return out[:max_items]

    def _resume_adjustments(self, apps: list, max_items: int) -> list[dict]:
        selector = ResumeStrategySelector(self._session)
        out: list[dict] = []
        for a in apps:
            if not a.job_description:
                continue
            rec = selector.recommend(a.job_description)
            out.append(
                {
                    "application_id": a.id,
                    "company": a.company,
                    "template_name": rec["template_name"],
                    "reason": rec["reason"],
                }
            )
            if len(out) >= max_items:
                break
        return out

    def _ats_opportunities(self, apps: list, max_items: int) -> list[dict]:
        # A draft application that has a JD is an un-analyzed ATS opportunity.
        return [
            {"application_id": a.id, "company": a.company, "position": a.position}
            for a in apps
            if a.job_description and a.status == "draft"
        ][:max_items]

    def _follow_ups(self, apps: list) -> list[dict]:
        return [
            {
                "application_id": a.id,
                "company": a.company,
                "position": a.position,
                "status": a.status,
            }
            for a in apps
            if a.status in _ACTIVE_STATUSES
        ]
