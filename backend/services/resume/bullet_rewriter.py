from __future__ import annotations

import re

# ── Allowed action verbs (per Resume Engine Spec v1.0) ──────────────────────
ACTION_VERBS: frozenset[str] = frozenset({
    "built", "led", "developed", "created", "designed", "automated", "generated",
    "implemented", "scaled", "optimized", "improved", "reduced", "analyzed",
    "architected", "managed", "directed", "partnered", "deployed", "delivered",
    "launched", "streamlined", "accelerated", "drove", "established", "expanded",
    "championed", "pioneered", "mentored", "evaluated", "integrated", "overhauled",
    "spearheaded",
})

# ── Filler replacement map ───────────────────────────────────────────────────
# Ordered longest-first so longer patterns match before their substrings do.
_FILLER_REPLACEMENTS: list[tuple[str, str]] = [
    (r"(?i)responsible\s+for\s*", ""),
    (r"(?i)in\s+order\s+to\b", "to"),
    (r"(?i)multiple\s+different\b", "multiple"),
    (r"(?i)a\s+number\s+of\b", ""),
    (r"(?i)worked\s+with\b", "partnered with"),
    (r"(?i)\bhelped\b", "Supported"),
    (r"(?i)\butilized\b", "Used"),
    (r"(?i)\bleveraged\b", "Used"),
    (r"(?i)\bsuccessfully\b", ""),
    (r"(?i)\bvarious\b", ""),
]

# Pre-compiled for performance
_COMPILED: list[tuple[re.Pattern[str], str]] = [
    (re.compile(pat), repl) for pat, repl in _FILLER_REPLACEMENTS
]

_MULTI_SPACE = re.compile(r" {2,}")


class BulletRewriter:
    """Clean, normalize, and compact resume bullet text.

    Non-destructive: always returns new strings, never modifies originals.
    """

    def normalize(self, text: str) -> str:
        """Apply filler-phrase replacement rules."""
        for pattern, replacement in _COMPILED:
            text = pattern.sub(replacement, text)
        return _MULTI_SPACE.sub(" ", text).strip()

    def enforce_action_verb(self, text: str) -> str:
        """Prepend 'Led ' if the bullet does not start with an allowed action verb."""
        first_word = text.split()[0].lower().rstrip(".,;:") if text.split() else ""
        if first_word in ACTION_VERBS:
            return text
        return f"Led {text}"

    def compress(self, text: str) -> str:
        """Normalize + enforce action verb."""
        return self.enforce_action_verb(self.normalize(text))

    def force_single_line(self, text: str, max_chars: int = 88) -> str:
        """Compress then truncate with '...' if still over max_chars."""
        compressed = self.compress(text)
        if len(compressed) <= max_chars:
            return compressed
        return compressed[: max_chars - 3] + "..."
