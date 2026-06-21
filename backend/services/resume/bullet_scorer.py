from __future__ import annotations

import re

# ── Signal keyword sets ──────────────────────────────────────────────────────

_IMPACT_KEYWORDS: frozenset[str] = frozenset({
    "$", "%", "revenue", "growth", "saved", "save", "reduced", "reduce",
    "increased", "increase", "generated", "generate", "profit", "cost",
    "million", "billion", "budget", "efficiency", "performance",
})

_LEADERSHIP_KEYWORDS: frozenset[str] = frozenset({
    "led", "lead", "managed", "manage", "recruited", "recruit",
    "built", "build", "directed", "direct", "owned", "own",
    "mentored", "mentor", "oversaw", "oversee", "spearheaded",
    "championed", "established",
})

_QUANT_PATTERN = re.compile(
    r'\d+[\d,]*\s*%'
    r'|\$[\d,]+'
    r'|[\d,]+\s*(?:million|billion|k\b)'
    r'|\d+x\b'
    r'|\b\d+\b',
    re.IGNORECASE,
)

_TECHNICAL_KEYWORDS: frozenset[str] = frozenset({
    "built", "engineered", "designed", "developed", "architected", "automated",
    "deployed", "implemented", "optimized", "integrated", "coded", "programmed",
    "pipeline", "api", "system", "database", "infrastructure",
})

_STRATEGIC_KEYWORDS: frozenset[str] = frozenset({
    "strategy", "strategic", "roadmap", "vision", "prioritized", "planned",
    "forecasted", "positioned", "defined", "shaped", "aligned",
})

_CROSS_FUNCTIONAL_KEYWORDS: frozenset[str] = frozenset({
    "cross-functional", "stakeholder", "partnered", "collaborated", "liaised",
    "coordinated", "facilitated", "negotiated", "communicated", "across teams",
})

# confidence → weight for context-aware scoring
_CONFIDENCE_WEIGHTS: dict[str, float] = {
    "verified": 1.0,
    "strong_inference": 0.7,
    "weak_inference": 0.3,
}


class BulletScorer:
    """Score resume bullets on five dimensions per the Resume Engine Spec v1.0.

    Weights: impact=0.35, quantification=0.25, keyword=0.20, leadership=0.10, uniqueness=0.10
    """

    WEIGHTS: dict[str, float] = {
        "impact": 0.35,
        "quantification": 0.25,
        "keyword": 0.20,
        "leadership": 0.10,
        "uniqueness": 0.10,
    }

    def score(
        self,
        bullet: dict,
        keywords: list[str],
        relevance_score: float = 0.5,
        already_selected: list[dict] | None = None,
    ) -> float:
        """Return composite score. See ``score_dimensions`` for per-dimension breakdown."""
        return sum(self.score_dimensions(bullet, keywords, relevance_score, already_selected).values())

    def score_dimensions(
        self,
        bullet: dict,
        keywords: list[str],
        relevance_score: float = 0.5,
        already_selected: list[dict] | None = None,
    ) -> dict[str, float]:
        """Return weighted per-dimension scores (all sum to the composite score).

        Keys: impact, quantification, keyword, leadership, uniqueness
        """
        text = bullet.get("bullet_text", "")
        text_lower = text.lower()

        impact = self._impact_score(text_lower)
        quant = 1.0 if _QUANT_PATTERN.search(text) else 0.0
        kw = self._keyword_score(text_lower, keywords)
        leadership = self._leadership_score(text_lower)
        uniqueness = self._uniqueness_score(text, already_selected or [])

        blended_impact = (impact + relevance_score) / 2.0

        return {
            "impact": self.WEIGHTS["impact"] * blended_impact,
            "quantification": self.WEIGHTS["quantification"] * quant,
            "keyword": self.WEIGHTS["keyword"] * kw,
            "leadership": self.WEIGHTS["leadership"] * leadership,
            "uniqueness": self.WEIGHTS["uniqueness"] * uniqueness,
        }

    def score_many(
        self,
        bullets: list[dict],
        keywords: list[str],
    ) -> list[dict]:
        """Score all bullets, enforce uniqueness across the set, sort descending.

        Returns bullets with added ``score`` key.
        """
        if not bullets:
            return []

        selected_so_far: list[dict] = []
        scored: list[dict] = []

        for i, b in enumerate(bullets):
            relevance = float(b.get("relevance_score", max(0.0, 1.0 - i * 0.05)))
            s = self.score(b, keywords, relevance, already_selected=selected_so_far)
            scored_bullet = {**b, "score": s}
            scored.append(scored_bullet)
            selected_so_far.append(b)

        return sorted(scored, key=lambda x: x["score"], reverse=True)

    # ── Phase 10 context-aware scoring ───────────────────────────────────────

    def score_with_context(
        self,
        bullet: dict,
        relevance: float,
        *,
        covered_dimensions: set[str] | None = None,
    ) -> float:
        """Composite 0..1 score blending relevance, confidence, dimension coverage, recency.

        score = 0.4·relevance + 0.3·confidence + 0.2·coverage_bonus + 0.1·recency

        coverage_bonus is 1.0 when the bullet's dominant dimension is not yet
        covered (rewards diversity), else 0.0.
        """
        confidence_weight = _CONFIDENCE_WEIGHTS.get(bullet.get("confidence", ""), 0.3)
        recency_weight = self._recency_weight(bullet)
        dimension = self.dominant_dimension(bullet.get("bullet_text", ""))
        covered = covered_dimensions or set()
        coverage_bonus = 0.0 if dimension in covered else 1.0

        return (
            0.4 * max(0.0, min(1.0, relevance))
            + 0.3 * confidence_weight
            + 0.2 * coverage_bonus
            + 0.1 * recency_weight
        )

    def dominant_dimension(self, text: str) -> str:
        """Classify a bullet into its strongest of the 5 resume dimensions."""
        text_lower = text.lower()
        scores = {
            "impact": sum(1 for k in _IMPACT_KEYWORDS if k in text_lower),
            "leadership": sum(1 for k in _LEADERSHIP_KEYWORDS if k in text_lower),
            "technical": sum(1 for k in _TECHNICAL_KEYWORDS if k in text_lower),
            "strategic": sum(1 for k in _STRATEGIC_KEYWORDS if k in text_lower),
            "cross_functional": sum(1 for k in _CROSS_FUNCTIONAL_KEYWORDS if k in text_lower),
        }
        best = max(scores, key=lambda d: scores[d])
        return best if scores[best] > 0 else "impact"

    def _recency_weight(self, bullet: dict) -> float:
        """current=1.0, ≤2yr=0.8, ≤5yr=0.6, else 0.4."""
        if bullet.get("is_current"):
            return 1.0
        years = bullet.get("years_ago")
        if years is None:
            return 0.6
        if years <= 2:
            return 0.8
        if years <= 5:
            return 0.6
        return 0.4

    # ── Private helpers ──────────────────────────────────────────────────────

    def _impact_score(self, text_lower: str) -> float:
        """1.0 if any impact keyword present, 0.0 otherwise."""
        return 1.0 if any(kw in text_lower for kw in _IMPACT_KEYWORDS) else 0.0

    def _leadership_score(self, text_lower: str) -> float:
        """1.0 if any leadership keyword present, 0.0 otherwise."""
        return 1.0 if any(kw in text_lower for kw in _LEADERSHIP_KEYWORDS) else 0.0

    def _keyword_score(self, text_lower: str, keywords: list[str]) -> float:
        """Fraction of JD keywords present in bullet (0.0 if no keywords)."""
        if not keywords:
            return 0.0
        matches = sum(1 for kw in keywords if kw.lower() in text_lower)
        return min(1.0, matches / len(keywords))

    def _uniqueness_score(self, text: str, already_selected: list[dict]) -> float:
        """1.0 for a novel bullet; penalised proportionally to word overlap with selected."""
        if not already_selected:
            return 1.0
        words = set(text.lower().split())
        if not words:
            return 1.0
        max_overlap = max(
            len(words & set(b.get("bullet_text", "").lower().split())) / len(words)
            for b in already_selected
        )
        return max(0.0, 1.0 - max_overlap)
