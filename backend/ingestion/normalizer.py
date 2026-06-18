from __future__ import annotations

import re


def normalize(text: str) -> str:
    """Normalize whitespace and line endings in ingested text.

    - Converts Windows (CRLF) and old Mac (CR) line endings to LF.
    - Collapses 3+ consecutive blank lines to a single blank line.
    - Collapses runs of spaces and tabs to a single space.
    - Strips leading/trailing whitespace.
    """
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]+", " ", text)
    return text.strip()
