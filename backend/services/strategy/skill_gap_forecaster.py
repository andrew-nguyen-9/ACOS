"""U5 — Skill Gap Forecaster.

Identifies skills that appear in recent JDs but are missing or weak in the
user's profile. Ranks by expected interview lift per hour invested.
"""
from __future__ import annotations

import logging
import re
from collections import Counter

from sqlalchemy.orm import Session

from backend.repositories.outcome import OutcomeSignalRepository
from backend.repositories.skill import SkillRepository

logger = logging.getLogger(__name__)

_HOURS_TO_ACQUIRE: dict[str, float] = {
    "python": 40, "sql": 20, "tableau": 10, "power bi": 8,
    "scikit-learn": 20, "fastapi": 15, "docker": 10, "kubernetes": 30,
    "dbt": 12, "airflow": 15, "spark": 25, "tensorflow": 40,
    "react": 30, "typescript": 20, "terraform": 20, "aws": 40,
    "looker": 8, "snowflake": 10, "bigquery": 8, "databricks": 15,
    "pytorch": 40, "excel": 5, "jira": 4, "confluence": 4,
}
_DEFAULT_HOURS = 40.0

_WEAK_PROFICIENCIES = {"exposure", "beginner"}


def _tokenize(text: str) -> list[str]:
    return [w.lower() for w in re.findall(r"[a-zA-Z0-9#+\-.]{2,}", text)]


class SkillGapForecaster:
    def __init__(self, session: Session) -> None:
        self._session = session

    def forecast(self) -> list[dict]:
        repo_outcome = OutcomeSignalRepository(self._session)
        repo_skill = SkillRepository(self._session)

        signals = repo_outcome.list()
        user_skills = {s.name.lower(): s.proficiency for s in repo_skill.list()}

        # Count how often each skill-like token appears in position_type / industry of missed signals
        missed_signals = [s for s in signals if s.signal_weight <= 0.3]
        interview_signals = [s for s in signals if s.signal_weight > 0.3]

        # Build token frequency from missed applications (proxy for "what I'm failing at")
        missed_tokens: Counter[str] = Counter()
        for s in missed_signals:
            for t in _tokenize((s.position_type or "") + " " + (s.industry or "")):
                missed_tokens[t] += 1

        # What skills did interview signals have in common?
        interview_tokens: Counter[str] = Counter()
        for s in interview_signals:
            for t in _tokenize((s.position_type or "") + " " + (s.industry or "")):
                interview_tokens[t] += 1

        # Only care about tokens that are in our known skills set OR hours table
        known = set(_HOURS_TO_ACQUIRE.keys())
        candidate_skills = (set(missed_tokens.keys()) | set(interview_tokens.keys())) & known

        gaps: list[dict] = []
        for skill in candidate_skills:
            proficiency = user_skills.get(skill)
            if proficiency in {"intermediate", "advanced", "expert"}:
                continue  # not a gap
            gap_type = "weak" if proficiency in _WEAK_PROFICIENCIES else "missing"
            freq = missed_tokens.get(skill, 0) + interview_tokens.get(skill, 0)
            blocking = missed_tokens.get(skill, 0)
            hours = _HOURS_TO_ACQUIRE.get(skill, _DEFAULT_HOURS)
            lift_per_hour = round(blocking / hours, 4) if hours > 0 else 0.0
            priority_rank = round(freq * (lift_per_hour or 0.01), 4)
            gaps.append(
                {
                    "skill_name": skill,
                    "gap_type": gap_type,
                    "frequency": freq,
                    "blocking_interviews": blocking,
                    "expected_lift_per_hour": lift_per_hour,
                    "priority_rank": priority_rank,
                }
            )

        gaps.sort(key=lambda g: g["priority_rank"], reverse=True)
        return gaps
