from __future__ import annotations

import hashlib
from pathlib import Path


MAX_FILE_BYTES = 52_428_800  # 50 MB


def validate_path(path: str, allowlist: list[str]) -> Path:
    resolved = Path(path).resolve()
    allowed_roots = [Path(a).resolve() for a in allowlist]
    for root in allowed_roots:
        try:
            resolved.relative_to(root)
            return resolved
        except ValueError:
            continue
    raise ValueError(f"Path '{resolved}' is not under any allowed directory: {allowlist}")


def validate_size(path: Path, max_bytes: int = MAX_FILE_BYTES) -> None:
    size = path.stat().st_size
    if size > max_bytes:
        raise ValueError(
            f"File '{path}' size {size} bytes exceeds limit of {max_bytes} bytes"
        )


def compute_checksum(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def sanitize_filename(name: str | None) -> str:
    """Return only the basename of *name*, replacing dangerous values with 'upload'.

    Strips all path separators so callers cannot traverse outside a temp dir.
    """
    if not name:
        return "upload"
    base = Path(name).name
    if not base or base in (".", ".."):
        return "upload"
    return base
