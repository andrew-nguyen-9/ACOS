from __future__ import annotations

import re
from dataclasses import dataclass, field

from backend.services.resume.bullet_rewriter import ACTION_VERBS
from backend.services.resume.layout_engine import MAX_PAGE_LINES, BULLET_WIDTH

# Max chars before a bullet is considered 3 lines (3 × 88 = 264, but spec says >176 is forbidden)
_MAX_BULLET_CHARS = BULLET_WIDTH * 2  # 176

_QUANT_PATTERN = re.compile(r"\d", re.IGNORECASE)

_FORBIDDEN_PHRASES = [
    "responsible for",
    "worked on",
    "helped with",
    "participated in",
    "assisted with",
]


@dataclass
class ValidationResult:
    valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


class ResumeValidator:
    """Validate a resume content dict before export.

    Errors block export; warnings are logged but do not block.
    """

    def validate(self, resume: dict) -> ValidationResult:
        errors: list[str] = []
        warnings: list[str] = []

        self._check_page_limit(resume, errors)

        for role in resume.get("experiences", []):
            bullets = role.get("bullets", [])
            bullet_texts = [b.get("text", "") if isinstance(b, dict) else str(b) for b in bullets]

            self._validate_action_verbs(bullet_texts, errors)
            self._validate_bullet_lengths(bullet_texts, errors)
            self._validate_quantification(bullet_texts, warnings)
            self._validate_role_density(bullet_texts, role.get("is_current", False), warnings)

        return ValidationResult(valid=len(errors) == 0, errors=errors, warnings=warnings)

    # ── Error checks ─────────────────────────────────────────────────────────

    def _check_page_limit(self, resume: dict, errors: list[str]) -> None:
        lines = resume.get("_estimated_lines", 0)
        if lines > MAX_PAGE_LINES:
            errors.append(
                f"Resume exceeds page limit: {lines} lines (max {MAX_PAGE_LINES})."
            )

    def _validate_action_verbs(self, bullets: list[str], errors: list[str]) -> None:
        for text in bullets:
            first = text.split()[0].lower().rstrip(".,;:") if text.split() else ""
            if first and first not in ACTION_VERBS:
                errors.append(
                    f"Bullet does not start with an allowed action verb: '{text[:60]}...'"
                )

    def _validate_bullet_lengths(self, bullets: list[str], errors: list[str]) -> None:
        for text in bullets:
            if len(text) > _MAX_BULLET_CHARS:
                errors.append(
                    f"Bullet too long ({len(text)} chars > {_MAX_BULLET_CHARS} max): "
                    f"'{text[:40]}...'"
                )

    # ── Warning checks ────────────────────────────────────────────────────────

    def _validate_quantification(self, bullets: list[str], warnings: list[str]) -> None:
        if not bullets:
            return
        quantified = sum(1 for b in bullets if _QUANT_PATTERN.search(b))
        ratio = quantified / len(bullets)
        if ratio < 0.30:
            warnings.append(
                f"Only {quantified}/{len(bullets)} bullets are quantified "
                f"({ratio:.0%} < 30% target)."
            )

    def _validate_role_density(
        self,
        bullets: list[str],
        is_current: bool,
        warnings: list[str],
    ) -> None:
        cap = 6 if is_current else 4
        role_type = "current" if is_current else "previous"
        if len(bullets) > cap:
            warnings.append(
                f"{role_type.capitalize()} role has {len(bullets)} bullets "
                f"(max {cap} recommended)."
            )
