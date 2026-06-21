from __future__ import annotations

import re

# alias → canonical skill name. Prevents synonyms occupying separate embedding clusters.
_ALIASES: dict[str, str] = {
    "ml": "machine learning",
    "nlp": "natural language processing",
    "a/b": "A/B testing",
    "ab testing": "A/B testing",
    "pm": "product management",
    "k8s": "Kubernetes",
    "ci/cd": "continuous integration",
    "dl": "deep learning",
    "bi": "business intelligence",
}


class SkillNormalizer:
    """Canonicalize skill aliases so synonyms cluster together in embedding space.

    Whole-token, case-insensitive replacement — never rewrites substrings of
    larger words (e.g. "ml" inside "HTML" is left alone).
    """

    def __init__(self) -> None:
        # Longest alias first so multi-word aliases match before their parts.
        self._patterns = [
            (re.compile(rf"(?<![\w/]){re.escape(alias)}(?![\w/])", re.IGNORECASE), canonical)
            for alias, canonical in sorted(_ALIASES.items(), key=lambda kv: -len(kv[0]))
        ]

    def normalize(self, text: str) -> str:
        for pattern, canonical in self._patterns:
            text = pattern.sub(canonical, text)
        return text

    def normalize_list(self, skills: list[str]) -> list[str]:
        """Canonicalize each skill and dedup, preserving first-seen order."""
        seen: set[str] = set()
        out: list[str] = []
        for skill in skills:
            canon = self.normalize(skill)
            key = canon.lower()
            if key not in seen:
                seen.add(key)
                out.append(canon)
        return out
