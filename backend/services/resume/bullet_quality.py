"""
backend/services/resume/bullet_quality.py

Style-guide quality checker for resume bullets.

Encodes rules from:
  • Harvard FAS Resume Quick Tips
  • WIT Coop & Careers Resume Grammar Guide
  • Yale OCS Resume Action Verbs guide
  • Notre Dame / Smith School MBA Resume Guidelines

Returns a list of named violations. Each violation is a (code, message) pair
so callers can filter by severity or display category.

Usage:
    from backend.services.resume.bullet_quality import BulletQualityChecker
    checker = BulletQualityChecker()
    violations = checker.check("Was responsible for developing the pipeline")
    # → [("PASSIVE_OPENER", "Starts with passive/weak opener ('was responsible for')")]
"""
from __future__ import annotations

import re
from dataclasses import dataclass

# ── Patterns ─────────────────────────────────────────────────────────────────

# Passive voice: "was/were/has been/have been [past-participle]"
_PASSIVE_RE = re.compile(
    r"\b(?:was|were|has\s+been|have\s+been|had\s+been)\s+\w+(?:ed|en)\b",
    re.IGNORECASE,
)

# Helping-verb openers that weaken ownership (WIT guide)
_HELPING_OPENER_RE = re.compile(
    r"^(?:have|had|may|might|could|would|should|was\s+able\s+to|were\s+able\s+to)\b",
    re.IGNORECASE,
)

# -ly adverbs that add no meaning (WIT: "favor strong verbs over adverbs")
# Excluded: adverbs that quantify timing (weekly, daily, monthly, annually)
_WEAK_ADVERB_RE = re.compile(
    r"\b(?:effectively|efficiently|skillfully|consistently|continually|"
    r"seamlessly|dynamically|successfully|proactively|actively|"
    r"strategically|diligently|thoroughly)\b",
    re.IGNORECASE,
)

# Non-descript language (WIT guide: "be specific and explain your abilities")
_NON_DESCRIPT_RE = re.compile(
    r"\b(?:worked\s+on|observed|experience\s+(?:with|in)|assisted\s+with|"
    r"participated\s+in\s+(?:a|the|various))\b",
    re.IGNORECASE,
)

# First-person pronouns (all guides: "avoid personal pronouns")
_PRONOUN_RE = re.compile(r"\b(?:I|we|my|our|I\'m|I\'ve|we\'ve)\b")

# Passive opener phrases
_PASSIVE_OPENER_RE = re.compile(
    r"^(?:was\s+responsible\s+for|was\s+tasked\s+with|was\s+involved\s+in|"
    r"were\s+responsible\s+for|has\s+been|have\s+been)\b",
    re.IGNORECASE,
)

# Contraction patterns (Smith MBA: "avoid contractions")
_CONTRACTION_RE = re.compile(
    r"\b(?:didn't|wouldn't|couldn't|shouldn't|wasn't|weren't|don't|"
    r"doesn't|isn't|aren't|it's|that's|there's|they're|we're|I'm|"
    r"I've|we've)\b",
    re.IGNORECASE,
)

# Vague judgment words (Smith MBA: "state facts not judgments")
_VAGUE_JUDGMENT_RE = re.compile(
    r"\b(?:big|large|small|important|significant|major|minor|great|"
    r"excellent|outstanding|impressive|numerous|many|several|some)\b",
    re.IGNORECASE,
)


@dataclass
class QualityViolation:
    code: str
    message: str
    severity: str  # "error" | "warning" | "suggestion"


class BulletQualityChecker:
    """Checks resume bullets against style guidelines from four sources.

    Returns a list of QualityViolation objects. Callers decide how to surface
    them (as validator warnings, UI hints, or report annotations).
    """

    def check(self, text: str) -> list[QualityViolation]:
        """Return all style violations found in *text*."""
        violations: list[QualityViolation] = []

        # ── Errors (block quality standard) ─────────────────────────────────
        if _PASSIVE_OPENER_RE.search(text):
            violations.append(QualityViolation(
                code="PASSIVE_OPENER",
                message=f"Starts with passive/weak opener — rewrite to lead with action verb",
                severity="error",
            ))

        if _HELPING_OPENER_RE.search(text):
            violations.append(QualityViolation(
                code="HELPING_VERB",
                message="Starts with a helping verb (have/had/may/might) — take ownership of the action",
                severity="error",
            ))

        if _PRONOUN_RE.search(text):
            violations.append(QualityViolation(
                code="PRONOUN",
                message="Contains first-person pronoun (I/we/my/our) — omit per all resume guides",
                severity="error",
            ))

        # ── Warnings (degrade quality) ────────────────────────────────────────
        if _PASSIVE_RE.search(text) and not _PASSIVE_OPENER_RE.search(text):
            violations.append(QualityViolation(
                code="PASSIVE_VOICE",
                message="Contains passive voice ('was developed', 'were created') — prefer active construction",
                severity="warning",
            ))

        m = _WEAK_ADVERB_RE.search(text)
        if m:
            violations.append(QualityViolation(
                code="WEAK_ADVERB",
                message=f"Weak adverb '{m.group()}' — remove and let the verb carry the weight (WIT guide)",
                severity="warning",
            ))

        if _NON_DESCRIPT_RE.search(text):
            violations.append(QualityViolation(
                code="NON_DESCRIPT",
                message="Non-descript phrasing detected ('worked on', 'experience with', 'assisted with') "
                        "— use specific action verbs (WIT guide)",
                severity="warning",
            ))

        if _CONTRACTION_RE.search(text):
            violations.append(QualityViolation(
                code="CONTRACTION",
                message="Contains contraction — expand to full form (Smith MBA guideline)",
                severity="warning",
            ))

        # ── Suggestions (optional improvements) ──────────────────────────────
        m2 = _VAGUE_JUDGMENT_RE.search(text)
        if m2:
            violations.append(QualityViolation(
                code="VAGUE_JUDGMENT",
                message=f"Vague word '{m2.group()}' — replace with specific fact or metric "
                        "(Smith MBA: 'state facts, not judgments')",
                severity="suggestion",
            ))

        if not re.search(r"\d", text):
            violations.append(QualityViolation(
                code="NO_QUANTIFICATION",
                message="No number found — add metric ($, %, count, time) per SAR/PAR format",
                severity="suggestion",
            ))

        if len(text) > 176:
            violations.append(QualityViolation(
                code="TOO_LONG",
                message=f"Bullet is {len(text)} chars (>176) — split into two bullets",
                severity="warning",
            ))

        return violations

    def check_many(self, texts: list[str]) -> dict[str, list[QualityViolation]]:
        """Check a list of bullet texts. Returns {text: violations}."""
        return {t: self.check(t) for t in texts}

    def summary(self, texts: list[str]) -> dict[str, int]:
        """Count violation codes across a list of bullets."""
        counts: dict[str, int] = {}
        for t in texts:
            for v in self.check(t):
                counts[v.code] = counts.get(v.code, 0) + 1
        return counts
