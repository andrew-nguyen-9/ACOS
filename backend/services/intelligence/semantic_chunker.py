from __future__ import annotations

import re

# Split on semicolons or sentence boundaries (period/!/? followed by whitespace).
_SPLIT = re.compile(r";|(?<=[.!?])\s+")


class SemanticChunker:
    """Split compound bullets into atomic clauses for independent embedding.

    A bullet like "Did X; achieved Y; resulting in Z" becomes three chunks,
    each embedded separately but sharing the same source evidence id upstream.
    """

    def __init__(self, min_chunk_len: int = 3) -> None:
        self._min = min_chunk_len

    def chunk(self, text: str) -> list[str]:
        if not text or not text.strip():
            return []
        parts = (p.strip().rstrip(".") for p in _SPLIT.split(text))
        return [p for p in parts if len(p) >= self._min]
