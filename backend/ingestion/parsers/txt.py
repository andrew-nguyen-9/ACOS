from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def parse(path: Path) -> str:
    try:
        for encoding in ("utf-8", "utf-8-sig", "latin-1"):
            try:
                return path.read_text(encoding=encoding)
            except UnicodeDecodeError:
                continue
        logger.warning("txt_parser: could not decode %s, returning empty", path)
        return ""
    except Exception as exc:
        logger.warning("txt_parser: failed to read %s: %s", path, exc)
        return ""
