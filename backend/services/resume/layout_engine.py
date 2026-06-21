from __future__ import annotations

import math
from dataclasses import dataclass

# ── Layout constants (per Resume Engine Spec v1.0) ──────────────────────────
MAX_PAGE_LINES = 60
BULLET_WIDTH = 88
CONTINUATION_WIDTH = 92
POSITION_HEADER_LINES = 2
SECTION_HEADER_LINES = 1
RESUME_HEADER_LINES = 3  # name + contact line + divider


@dataclass
class LayoutResult:
    total_lines: int
    remaining_lines: int
    fits: bool


class LayoutEngine:
    """Estimate whether a resume content dict fits on one page.

    Uses character-width heuristics (88 chars/line for bullets, 60 lines max).
    Phase 8.2 will replace this with true DOCX→PDF page measurement.
    """

    def estimate_text_lines(self, text: str, width: int) -> int:
        return max(1, math.ceil(len(text) / width)) if text else 1

    def estimate_bullet_lines(self, bullet: str) -> int:
        return self.estimate_text_lines(bullet, BULLET_WIDTH)

    def estimate_role_lines(self, role: dict) -> int:
        total = POSITION_HEADER_LINES
        for bullet in role.get("bullets", []):
            text = bullet.get("text", "") if isinstance(bullet, dict) else str(bullet)
            total += self.estimate_bullet_lines(text)
        return total

    def estimate_resume(self, resume: dict) -> LayoutResult:
        """Estimate total line count for a resume dict.

        Expected keys:
            experiences: list of role dicts (each with ``bullets`` list)
            header_lines: override for the name/contact block (default RESUME_HEADER_LINES)
        """
        total = resume.get("header_lines", RESUME_HEADER_LINES)

        experiences = resume.get("experiences", [])
        if experiences:
            total += SECTION_HEADER_LINES
            for role in experiences:
                total += self.estimate_role_lines(role)

        remaining = max(0, MAX_PAGE_LINES - total)
        return LayoutResult(
            total_lines=total,
            remaining_lines=remaining,
            fits=total <= MAX_PAGE_LINES,
        )

    def overflow_amount(self, resume: dict) -> int:
        """Lines over the page limit; 0 if the resume fits."""
        result = self.estimate_resume(resume)
        return max(0, result.total_lines - MAX_PAGE_LINES)
