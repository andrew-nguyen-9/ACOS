from __future__ import annotations

import re
from pathlib import Path

from backend.ingestion.parsers.txt import parse as parse_txt

_MD_INLINE = re.compile(r"[*_`~]{1,3}(.*?)[*_`~]{1,3}", re.DOTALL)
_MD_HEADING = re.compile(r"^#{1,6}\s+", re.MULTILINE)
_MD_LINK = re.compile(r"\[([^\]]+)\]\([^)]+\)")
_MD_CODE_BLOCK = re.compile(r"```.*?```", re.DOTALL)


def parse(path: Path) -> str:
    raw = parse_txt(path)
    text = _MD_CODE_BLOCK.sub("", raw)
    text = _MD_HEADING.sub("", text)
    text = _MD_LINK.sub(r"\1", text)
    text = _MD_INLINE.sub(r"\1", text)
    return text.strip()
