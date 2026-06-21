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
        """Return composite score.

        Args:
            bullet: dict with at least ``bullet_text`` key.
            keywords: JD keywords for keyword-density scoring.
            relevance_score: 0.0–1.0 from reranker; used to weight impact dimension.
            already_selected: bullets already chosen; used for uniqueness penalty.

        Returns:
            Composite float score. Roughly 0.0–1.0 for typical bullets.
        """
        text = bullet.get("bullet_text", "")
        text_lower = text.lower()

        impact = self._impact_score(text_lower)
        quant = 1.0 if _QUANT_PATTERN.search(text) else 0.0
        kw = self._keyword_score(text_lower, keywords)
        leadership = self._leadership_score(text_lower)
        uniqueness = self._uniqueness_score(text, already_selected or [])

        # Blend relevance_score into impact dimension
        blended_impact = (impact + relevance_score) / 2.0

        return (
            self.WEIGHTS["impact"] * blended_impact
            + self.WEIGHTS["quantification"] * quant
            + self.WEIGHTS["keyword"] * kw
            + self.WEIGHTS["leadership"] * leadership
            + self.WEIGHTS["uniqueness"] * uniqueness
        )

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
