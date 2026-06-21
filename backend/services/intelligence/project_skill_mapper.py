from __future__ import annotations

import re

from backend.services.intelligence.query_understander import _SKILL_VOCAB


class ProjectSkillMapper:
    """Expand project text with inferred skills so skill-based retrieval matches projects.

    "Built a Tableau dashboard" → "Built a Tableau dashboard [skills: Tableau, data visualization]"
    Only appends skills found verbatim in the text (no invention).
    """

    def __init__(self) -> None:
        self._patterns = [
            (re.compile(rf"(?<!\w){re.escape(skill)}(?!\w)", re.IGNORECASE), skill)
            for skill in _SKILL_VOCAB
        ]

    def expand(self, text: str) -> str:
        found: list[str] = []
        for pattern, skill in self._patterns:
            if pattern.search(text) and skill not in found:
                found.append(skill)
        if not found:
            return text
        return f"{text} [skills: {', '.join(found)}]"
