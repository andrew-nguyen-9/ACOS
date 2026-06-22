"""U6 — Resume Strategy Selector.

Returns a template + bullet emphasis recommendation for a given JD.
Always returns requires_approval=True — caller must POST to /apply to execute.
"""
from __future__ import annotations

import logging
import re

from sqlalchemy.orm import Session

from backend.services.learning import anchors
from backend.services.strategy.career_path_simulator import CATEGORY_KEYWORDS

logger = logging.getLogger(__name__)

_BULLET_EMPHASIS: dict[str, list[str]] = {
    "product_management": ["leadership", "impact", "strategic"],
    "data_analytics": ["technical", "quantification", "impact"],
    "ai_ml": ["technical", "impact", "quantification"],
    "consulting": ["strategic", "impact", "leadership"],
    "litigation_consulting": ["technical", "impact", "strategic"],
    "tpm_solutions": ["leadership", "cross_functional", "impact"],
}

_TEMPLATE_MAP: dict[str, str] = {
    "product_management": "pm_executive",
    "data_analytics": "data_technical",
    "ai_ml": "data_technical",
    "consulting": "consulting_narrative",
    "litigation_consulting": "consulting_narrative",
    "tpm_solutions": "pm_executive",
}


def _detect_category(jd_text: str) -> str:
    jd_lower = jd_text.lower()
    best_cat = "product_management"
    best_score = 0
    for cat, keywords in CATEGORY_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw in jd_lower)
        if score > best_score:
            best_score = score
            best_cat = cat
    return best_cat


def _extract_top_keywords(jd_text: str, top_n: int = 10) -> list[str]:
    tokens = re.findall(r"[a-zA-Z][a-zA-Z0-9#+\-.]{2,}", jd_text)
    freq: dict[str, int] = {}
    for t in tokens:
        key = t.lower()
        freq[key] = freq.get(key, 0) + 1
    _STOP = {
        "and", "the", "for", "with", "will", "this", "that", "are",
        "you", "our", "from", "have", "your", "their", "has", "can",
    }
    ranked = sorted(
        [(w, c) for w, c in freq.items() if w not in _STOP],
        key=lambda x: x[1],
        reverse=True,
    )
    return [w for w, _ in ranked[:top_n]]


class ResumeStrategySelector:
    def __init__(self, session: Session) -> None:
        self._session = session

    def recommend(self, jd_text: str) -> dict:
        category = _detect_category(jd_text)
        template = _TEMPLATE_MAP.get(category, "pm_executive")
        emphasis = _BULLET_EMPHASIS.get(category, ["impact", "leadership", "technical"])
        keywords = _extract_top_keywords(jd_text)
        # Success anchoring (11.3): always *consider* proven high-success
        # strategies, immune to recency-only drift. Added to candidates, not
        # pinned to output — the detected template stays the recommendation.
        anchored = anchors.select_anchors(self._session)
        reason = (
            f"Detected role category '{category}'. "
            f"Template '{template}' maximizes readability for this category. "
            f"Emphasis on {emphasis[0]} and {emphasis[1]} bullets aligns with historical signal patterns."
        )
        if anchored:
            reason += (
                f" Also considering proven anchor(s): "
                f"{', '.join(a['template_name'] for a in anchored)}."
            )
        return {
            "template_name": template,
            "bullet_emphasis": emphasis,
            "keyword_priorities": keywords,
            "reason": reason,
            "anchored_candidates": anchored,
            "requires_approval": True,
        }
