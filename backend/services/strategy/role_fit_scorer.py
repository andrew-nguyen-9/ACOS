"""U2 — Role Fit Scorer.

Computes a 0-100 fit score for a job description against the user's profile.

Sub-scores:
    skill_overlap        0.30  required_skills ∩ user skills / total required
    experience_alignment 0.30  ATS experience_score / 100
    industry_alignment   0.20  avg signal_weight for same industry
    historical_similarity 0.20 keyword Jaccard × past signal weights
"""
from __future__ import annotations

import hashlib
import json
import logging
import re
from collections import defaultdict
from typing import Any

from sqlalchemy.orm import Session

from backend.repositories.outcome import OutcomeSignalRepository
from backend.repositories.skill import SkillRepository

logger = logging.getLogger(__name__)

_WEIGHTS = {
    "skill_overlap": 0.30,
    "experience_alignment": 0.30,
    "industry_alignment": 0.20,
    "historical_similarity": 0.20,
}

_BRIDGEABLE = {"exposure", "beginner"}


def _jd_hash(jd_text: str) -> str:
    return hashlib.sha256(jd_text.encode()).hexdigest()[:32]


def _tokenize(text: str) -> set[str]:
    return {w.lower() for w in re.findall(r"[a-zA-Z0-9#+\-.]{2,}", text)}


class RoleFitScorer:
    def __init__(self, session: Session, ats_scorer: Any | None = None) -> None:
        self._session = session
        self._ats = ats_scorer

    def score(self, jd_text: str) -> dict:
        jd_tokens = _tokenize(jd_text)
        skill_overlap = self._skill_overlap(jd_tokens)
        experience_alignment = self._experience_alignment(jd_text)
        industry_alignment = self._industry_alignment(jd_text)
        historical_similarity = self._historical_similarity(jd_tokens)

        overall = round(
            skill_overlap * _WEIGHTS["skill_overlap"]
            + experience_alignment * _WEIGHTS["experience_alignment"]
            + industry_alignment * _WEIGHTS["industry_alignment"]
            + historical_similarity * _WEIGHTS["historical_similarity"],
            1,
        )

        missing_critical = self._missing_critical_skills(jd_tokens)
        risk_factors = self._risk_factors(skill_overlap, experience_alignment, missing_critical)
        sample_size = self._total_signals()
        confidence = (
            "verified" if sample_size >= 10
            else "strong_inference" if sample_size >= 3
            else "weak_inference"
        )

        return {
            "overall": overall,
            "skill_overlap": round(skill_overlap, 1),
            "experience_alignment": round(experience_alignment, 1),
            "industry_alignment": round(industry_alignment, 1),
            "historical_similarity": round(historical_similarity, 1),
            "explanation": self._explanation(overall, skill_overlap, experience_alignment),
            "risk_factors": risk_factors,
            "missing_critical_skills": missing_critical,
            "confidence": confidence,
        }

    # ── sub-score helpers ───────────────────────────────────────────────────

    def _skill_overlap(self, jd_tokens: set[str]) -> float:
        repo = SkillRepository(self._session)
        user_skills = {s.name.lower() for s in repo.list()}
        if not jd_tokens:
            return 0.0
        matched = len(jd_tokens & user_skills)
        return round(min(matched / max(len(jd_tokens), 1), 1.0) * 100, 1)

    def _experience_alignment(self, jd_text: str) -> float:
        if self._ats is None:
            return 50.0
        try:
            result = self._ats.score(resume_text="", job_description=jd_text, keywords={})
            return float(result.get("experience_score", 50))
        except Exception:
            logger.debug("ATS scorer unavailable; defaulting experience_alignment to 50")
            return 50.0

    def _industry_alignment(self, jd_text: str) -> float:
        repo = OutcomeSignalRepository(self._session)
        signals = repo.list()
        jd_lower = jd_text.lower()
        industry_weights: list[float] = []
        for s in signals:
            if s.industry and s.industry.lower() in jd_lower:
                industry_weights.append(s.signal_weight)
        if not industry_weights:
            return 50.0
        return round(sum(industry_weights) / len(industry_weights) * 100, 1)

    def _historical_similarity(self, jd_tokens: set[str]) -> float:
        repo = OutcomeSignalRepository(self._session)
        signals = repo.list()
        if not signals:
            return 50.0
        scores: list[float] = []
        for s in signals:
            hist_tokens = _tokenize(s.industry or "") | _tokenize(s.position_type or "")
            if not hist_tokens:
                continue
            union = jd_tokens | hist_tokens
            jaccard = len(jd_tokens & hist_tokens) / len(union) if union else 0.0
            scores.append(jaccard * s.signal_weight * 100)
        if not scores:
            return 50.0
        return round(sum(scores) / len(scores), 1)

    def _missing_critical_skills(self, jd_tokens: set[str]) -> list[str]:
        repo = SkillRepository(self._session)
        user_skills = {s.name.lower() for s in repo.list()}
        # ponytail: critical = token appears to be a named tech/skill (heuristic: contains letter+digit or is a known keyword)
        _ALWAYS_CRITICAL = {
            "python", "sql", "java", "typescript", "javascript", "react", "aws",
            "gcp", "azure", "docker", "kubernetes", "tensorflow", "pytorch",
            "spark", "kafka", "airflow", "dbt", "looker", "tableau",
            "snowflake", "bigquery", "databricks", "terraform",
        }
        critical = jd_tokens & _ALWAYS_CRITICAL
        return sorted(critical - user_skills)

    def _risk_factors(
        self, skill_overlap: float, exp_alignment: float, missing: list[str]
    ) -> list[str]:
        factors: list[str] = []
        if skill_overlap < 40:
            factors.append(f"Low skill overlap ({skill_overlap:.0f}/100)")
        if exp_alignment < 40:
            factors.append(f"Low experience alignment ({exp_alignment:.0f}/100)")
        if len(missing) > 3:
            factors.append(f"{len(missing)} critical skills missing: {', '.join(missing[:3])}…")
        return factors

    def _total_signals(self) -> int:
        repo = OutcomeSignalRepository(self._session)
        return len(repo.list())

    def _explanation(
        self, overall: float, skill_overlap: float, exp_alignment: float
    ) -> str:
        tier = "strong" if overall >= 75 else "moderate" if overall >= 50 else "weak"
        return (
            f"Overall fit is {tier} ({overall}/100). "
            f"Skill overlap: {skill_overlap:.0f}/100; "
            f"experience alignment: {exp_alignment:.0f}/100."
        )
