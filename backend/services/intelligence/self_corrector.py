from __future__ import annotations

import re
from dataclasses import dataclass, field

from backend.services.intelligence.query_understander import _SKILL_VOCAB
from backend.services.resume.bullet_rewriter import BulletRewriter

# Two near-identical bullets share this much of their word set → treated as duplicates.
_DUP_OVERLAP_THRESHOLD = 0.8


@dataclass
class CorrectionResult:
    bullets: list[dict]
    corrections: list[str] = field(default_factory=list)
    requires_approval: bool = False
    hallucination_flags: list[str] = field(default_factory=list)


def _word_overlap(a: str, b: str) -> float:
    wa, wb = set(a.lower().split()), set(b.lower().split())
    if not wa or not wb:
        return 0.0
    return len(wa & wb) / len(wa | wb)


class SelfCorrector:
    """Final quality pass over generated bullets before export.

    Applies deterministic corrections: compress over-length bullets, deduplicate
    near-identical experiences (keeping the higher-scored one), flag skills not
    backed by evidence, and surface weak inferences for approval.
    """

    def __init__(self, rewriter: BulletRewriter | None = None, max_chars: int = 175) -> None:
        self._rewriter = rewriter or BulletRewriter()
        self._max_chars = max_chars
        self._skill_patterns = [
            (re.compile(rf"(?<!\w){re.escape(s)}(?!\w)", re.IGNORECASE), s)
            for s in _SKILL_VOCAB
        ]

    def correct(
        self,
        bullets: list[dict],
        allowed_skills: list[str] | None = None,
    ) -> CorrectionResult:
        result = CorrectionResult(bullets=[])

        deduped = self._dedup(bullets, result)

        for b in deduped:
            corrected = dict(b)
            text = corrected.get("bullet_text", "")

            if len(text) > self._max_chars:
                corrected["bullet_text"] = self._rewriter.force_single_line(text, self._max_chars)
                result.corrections.append(
                    f"compressed over-length bullet ({len(text)}>{self._max_chars} chars)"
                )

            if corrected.get("confidence") == "weak_inference":
                result.requires_approval = True

            if allowed_skills is not None:
                self._flag_hallucinated_skills(corrected["bullet_text"], allowed_skills, result)

            result.bullets.append(corrected)

        return result

    # ── Deduplication ───────────────────────────────────────────────────────────

    def _dedup(self, bullets: list[dict], result: CorrectionResult) -> list[dict]:
        """Drop near-duplicate bullets, keeping the higher-scored one of each pair."""
        # Highest score first so the survivor is always the keeper.
        ordered = sorted(bullets, key=lambda b: b.get("score", 0.0), reverse=True)
        kept: list[dict] = []
        for b in ordered:
            text = b.get("bullet_text", "")
            if any(_word_overlap(text, k.get("bullet_text", "")) >= _DUP_OVERLAP_THRESHOLD for k in kept):
                result.corrections.append("removed duplicate experience")
                continue
            kept.append(b)
        return kept

    # ── Hallucination check ───────────────────────────────────────────────────────

    def _flag_hallucinated_skills(
        self, text: str, allowed_skills: list[str], result: CorrectionResult
    ) -> None:
        allowed_lower = {s.lower() for s in allowed_skills}
        for pattern, skill in self._skill_patterns:
            if pattern.search(text) and skill.lower() not in allowed_lower:
                flag = f"'{skill}' claimed in bullet but absent from evidence"
                if flag not in result.hallucination_flags:
                    result.hallucination_flags.append(flag)
