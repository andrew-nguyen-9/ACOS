from __future__ import annotations

import hashlib
import zipfile
from pathlib import Path


MAX_FILE_BYTES = 52_428_800  # 50 MB

# 16.5: active-content markers we refuse to ingest. We never *execute* parsed
# content (parsers only read text), but a document carrying macros / embedded
# executables / PDF JavaScript is rejected up front rather than stored.
_DOCX_MACRO_MEMBERS = ("vbaproject.bin",)
_EXECUTABLE_SUFFIXES = (".exe", ".bat", ".cmd", ".scr", ".js", ".vbs", ".dll", ".com", ".jar")
_PDF_ACTIVE_MARKERS = (b"/JavaScript", b"/JS", b"/Launch", b"/EmbeddedFile")


class UnsafeFileError(ValueError):
    """File carries executable/macro/script content — refused before ingestion."""


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


def reject_active_content(path: Path) -> None:
    """16.5: refuse macros / embedded executables / PDF active content.

    Fails closed and quietly on an unreadable/garbage file — parse isolation
    handles malformed files elsewhere; this only blocks *recognizable* active
    content, never crashes on a fuzzed one.
    """
    suffix = path.suffix.lower()
    if suffix == ".docx":
        try:
            with zipfile.ZipFile(path) as zf:
                names = [n.lower() for n in zf.namelist()]
        except (zipfile.BadZipFile, OSError):
            return  # not a valid zip — the parser will fail-close to empty text
        for member in names:
            base = member.rsplit("/", 1)[-1]
            if base in _DOCX_MACRO_MEMBERS:
                raise UnsafeFileError(f"DOCX contains macros ({base})")
            if any(base.endswith(ext) for ext in _EXECUTABLE_SUFFIXES):
                raise UnsafeFileError(f"DOCX embeds an executable/script ({base})")
    elif suffix == ".pdf":
        try:
            head = path.read_bytes()
        except OSError:
            return
        for marker in _PDF_ACTIVE_MARKERS:
            if marker in head:
                raise UnsafeFileError(
                    f"PDF contains active content ({marker.decode(errors='ignore')})"
                )


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
