from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def parse(path: Path) -> str:
    try:
        from docx import Document
        doc = Document(str(path))
        return "\n".join(p.text for p in doc.paragraphs if p.text.strip())
    except Exception as exc:
        logger.warning("docx_parser: failed to parse %s: %s", path, exc)
        return ""
