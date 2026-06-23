"""Pydantic response schemas for Phase 9 Strategy API."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


ConfidenceTier = Literal["verified", "strong_inference", "weak_inference"]
JobPriorityAction = Literal["prioritize", "tailor", "bridge", "skip"]


class RoleFitScore(BaseModel):
    overall: float
    skill_overlap: float
    experience_alignment: float
    industry_alignment: float
    historical_similarity: float
    explanation: str
    risk_factors: list[str]
    missing_critical_skills: list[str]
    confidence: ConfidenceTier


class CareerPathResult(BaseModel):
    category: str
    interview_probability: float
    offer_probability: float
    expected_timeline_days: float | None
    difficulty_rating: float
    sample_size: int
    confidence: ConfidenceTier


class ApplicationPriority(BaseModel):
    job_id: str
    jd_snippet: str
    priority: JobPriorityAction
    reason: str
    fit_score: float
    # 15.1 enrichment (ADR-006/012): the ranked estimate carries its confidence +
    # the evidence it derived from; top_pick is server-decided, weak rows excluded.
    confidence: ConfidenceTier
    missing_critical_skills: list[str]
    risk_factors: list[str]
    explanation: str
    top_pick: bool


class ApplicationSuggestion(BaseModel):
    """15.2 — composed Apply/Skip/Tailor recommendation. Recommend-only (ADR-012).

    Every section is explained + confidence-tagged; the action the user takes is
    internal (mark status / open the tailor flow), never an external submit.
    """
    recommendation: Literal["apply", "tailor", "skip"]
    reason: str
    fit_score: float
    confidence: ConfidenceTier
    missing_critical_skills: list[str]
    risk_factors: list[str]
    explanation: str
    resume_template: str
    resume_reason: str
    cover_letter_tone: float
    cover_letter_tone_descriptor: str
    interview_probability: float
    interview_sample_size: int
    interview_confidence: ConfidenceTier
    interview_category: str


class SuggestionRequest(BaseModel):
    jd_text: str = Field(..., min_length=50)


class SkillGapItem(BaseModel):
    skill_name: str
    gap_type: Literal["missing", "weak"]
    frequency: int
    blocking_interviews: int
    expected_lift_per_hour: float
    priority_rank: float


class StrategyAnchor(BaseModel):
    template_name: str
    success_score: float
    signal_count: int


class ResumeStrategyRecommendation(BaseModel):
    template_name: str
    bullet_emphasis: list[str]
    keyword_priorities: list[str]
    reason: str
    anchored_candidates: list[StrategyAnchor] = Field(default_factory=list)
    requires_approval: Literal[True] = True


class OutcomeBucket(BaseModel):
    range: str
    outcome_rate: float
    count: int


class CategoryBreakdown(BaseModel):
    category: str
    total: int
    interview_rate: float
    offer_rate: float
    avg_signal_weight: float
    confidence: ConfidenceTier


class OutcomeReport(BaseModel):
    category_breakdown: list[CategoryBreakdown]
    ats_threshold: list[OutcomeBucket]
    total_signals: int


# ── Request schemas ────────────────────────────────────────────────────────────

class RoleFitRequest(BaseModel):
    jd_text: str = Field(..., min_length=50)


class PrioritizeRequest(BaseModel):
    jobs: list[dict] = Field(..., description="List of {job_id, jd_text} dicts")


class ResumeStrategyRequest(BaseModel):
    jd_text: str = Field(..., min_length=50)


class EnrichCorpusRequest(BaseModel):
    urls: list[str] = Field(default_factory=list, max_length=20)
    max_per_domain: int = Field(default=5, ge=1, le=20)
