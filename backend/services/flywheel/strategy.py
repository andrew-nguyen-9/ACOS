"""Phase 12.12 Resume Strategy Intelligence Layer.

Composes 12.11 skill ROI + 12.10 signal rollups + JD analysis into per-tenant resume
structure + ATS strategy recommendations. ADVISES the existing resume engine — it does
not generate resumes (plan §3).

Every recommendation is grounded in the tenant's own evidence and carries an ADR-006
confidence level. Sparse data degrades to ``weak_inference`` and unknown industries are
flagged + fall back to a generic structure — never a fabricated "best practice"
(CLAUDE.md non-negotiable #1).
"""
from __future__ import annotations

from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from backend.services.flywheel.skill_roi import rank_skills

# Defined industry taxonomy → recommended resume section ordering. Unknown industries
# resolve to ``generic`` and are flagged (Trap 2: no guessing).
INDUSTRY_STRUCTURES: dict[str, list[str]] = {
    "generic": ["summary", "experience", "skills", "education", "projects"],
    "technology": ["summary", "skills", "experience", "projects", "education"],
    "finance": ["summary", "experience", "education", "skills", "certifications"],
    "healthcare": ["summary", "experience", "certifications", "education", "skills"],
    "consulting": ["summary", "experience", "education", "skills", "projects"],
    "marketing": ["summary", "experience", "skills", "projects", "education"],
}


@dataclass
class StrategyRecommendation:
    industry: str
    section_order: list[str]
    recommended_skills: list[str]   # high-ROI skills to surface (12.11)
    keyword_targets: list[str]      # ATS keywords prioritized by ROI then JD order
    confidence: str                 # ADR-006 level
    flagged: bool                   # True when degraded (sparse data / unknown industry)
    evidence: list[str] = field(default_factory=list)  # contributing signal ids
    notes: str = ""


def _resolve_industry(raw: str | None) -> tuple[str, bool]:
    """Map a JD industry string to a taxonomy key. Unknown → ('generic', flagged=True)."""
    key = (raw or "").strip().lower()
    if key in INDUSTRY_STRUCTURES and key != "generic":
        return key, False
    return "generic", True


def recommend(
    session: Session,
    *,
    keywords: dict,
    tenant_id: str | None = None,
    metric: str = "interview_lift",
) -> StrategyRecommendation:
    """Per-tenant resume structure + ATS strategy for a JD (already keyword-extracted).

    ``keywords`` is the JD analysis from the ATS keyword extractor:
    ``{"required_skills": [...], "keywords": [...], "industry": str}``. The route does
    the extraction; this stays a pure, testable composition over signals + ROI.
    """
    industry, industry_flagged = _resolve_industry(keywords.get("industry"))
    section_order = INDUSTRY_STRUCTURES[industry]

    roi = rank_skills(session, tenant_id=tenant_id, metric=metric)
    recommended_skills = list(roi["recommended"])  # strong + positive ROI only
    by_skill = {s["skill"]: s for s in roi["skills"]}

    # ATS keyword targets: JD skills that are also high-ROI come first (ROI order),
    # then the remaining JD keywords in their original order. No invented keywords.
    jd_keywords = list(keywords.get("required_skills", [])) + list(keywords.get("keywords", []))
    roi_first = [s for s in recommended_skills if s in jd_keywords]
    rest = [k for k in jd_keywords if k not in roi_first]
    keyword_targets = roi_first + rest

    # Evidence = the contributing signal ids behind the surfaced high-ROI skills.
    evidence: list[str] = []
    for skill in recommended_skills:
        evidence.extend(by_skill[skill]["contributing_signal_ids"])

    # Confidence: a real ROI signal AND a known industry → strong; otherwise weak +
    # flagged (sparse local data or an industry we don't have a structure for).
    has_roi = bool(recommended_skills)
    if has_roi and not industry_flagged:
        confidence = "strong_inference"
        flagged = False
        notes = "Grounded in the tenant's own outcome signals."
    else:
        confidence = "weak_inference"
        flagged = True
        notes = (
            "Generic structure: "
            + ("unknown industry; " if industry_flagged else "")
            + ("insufficient outcome data" if not has_roi else "").strip("; ")
        ).strip()

    return StrategyRecommendation(
        industry=industry,
        section_order=section_order,
        recommended_skills=recommended_skills,
        keyword_targets=keyword_targets,
        confidence=confidence,
        flagged=flagged,
        evidence=evidence,
        notes=notes,
    )
