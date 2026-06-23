"""U4 — Application Strategy Engine.

Given a list of {job_id, jd_text} dicts, returns priority action per job.

Priority rules:
    fit_score >= 75 AND missing_critical <= 1  → prioritize
    fit_score 55-74                            → tailor
    fit_score 40-54 OR bridgeable gaps         → bridge
    fit_score < 40 OR missing_critical > 3     → skip
"""
from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from backend.repositories.skill import SkillRepository
from backend.services.strategy.role_fit_scorer import RoleFitScorer

logger = logging.getLogger(__name__)

_APPLY_WORTHY = {"prioritize", "tailor"}


def _mark_top_pick(rows: list[dict]) -> list[dict]:
    """Mark the single best apply-worthy, non-low-n row as the top pick.

    ADR-012 trap 3: low-n (``weak_inference``) estimates are excluded from
    "top pick" emphasis so the user is never nudged hard on thin evidence. Rows
    are already sorted by fit descending, so the first eligible one wins.
    """
    for r in rows:
        r["top_pick"] = False
    for r in rows:
        if r["confidence"] != "weak_inference" and r["priority"] in _APPLY_WORTHY:
            r["top_pick"] = True
            break
    return rows


class ApplicationStrategyEngine:
    def __init__(self, session: Session) -> None:
        self._session = session
        self._scorer = RoleFitScorer(session)

    def prioritize(self, jobs: list[dict]) -> list[dict]:
        results = []
        for job in jobs:
            job_id = job.get("job_id", "")
            jd_text = job.get("jd_text", "")
            if not jd_text:
                continue
            fit = self._scorer.score(jd_text)
            score = fit["overall"]
            missing = len(fit["missing_critical_skills"])
            action, reason = self._decide(score, missing, fit)
            results.append(
                {
                    "job_id": job_id,
                    "jd_snippet": jd_text[:200],
                    "priority": action,
                    "reason": reason,
                    "fit_score": score,
                    # ADR-012/006: carry the estimate's confidence + the evidence it
                    # came from — the surface never shows a bare number.
                    "confidence": fit["confidence"],
                    "missing_critical_skills": fit["missing_critical_skills"],
                    "risk_factors": fit["risk_factors"],
                    "explanation": fit["explanation"],
                }
            )
        results.sort(key=lambda r: r["fit_score"], reverse=True)
        return _mark_top_pick(results)

    def _decide(self, score: float, missing: int, fit: dict) -> tuple[str, str]:
        if score >= 75 and missing <= 1:
            return "prioritize", f"High fit ({score}/100) with {missing} critical gap(s). Apply now."
        if score >= 55:
            return "tailor", f"Good fit ({score}/100). Tailor bullets to missing keywords."
        if score >= 40 or (missing > 0 and self._has_bridgeable(fit)):
            return "bridge", f"Moderate fit ({score}/100). Address skill gaps before applying."
        return "skip", f"Low fit ({score}/100) with {missing} critical gap(s). ROI likely low."

    def _has_bridgeable(self, fit: dict) -> bool:
        repo = SkillRepository(self._session)
        skills = {s.name.lower(): s.proficiency for s in repo.list()}
        _BRIDGEABLE = {"exposure", "beginner"}
        for skill_name in fit.get("missing_critical_skills", []):
            prof = skills.get(skill_name.lower())
            if prof in _BRIDGEABLE:
                return True
        return False
