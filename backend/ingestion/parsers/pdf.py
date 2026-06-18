from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def parse(path: Path) -> str:
    try:
        from pypdf import PdfReader
        reader = PdfReader(str(path), strict=False)
        parts = []
        for page in reader.pages:
            try:
                text = page.extract_text()
                if text:
                    parts.append(text)
            except Exception as exc:
                logger.warning("pdf_parser: page extraction failed in %s: %s", path, exc)
        return "\n".join(parts)
    except Exception as exc:
        logger.warning("pdf_parser: failed to parse %s: %s", path, exc)
        return ""
