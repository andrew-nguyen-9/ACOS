"""Phase 18.1 — the public repo ships no developer personal identifiers (Q11).

Scans shipped source (backend non-test + frontend/src non-test). Test fixtures may
use sample names; the seeded Andrew corpus lives only in gitignored .static_files/.
"""
from __future__ import annotations

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
IDENTIFIERS = ["andrew-nguyen", "andrewng9999", "andrew nguyen"]


def _shipped_files() -> list[Path]:
    files: list[Path] = []
    for base, patterns in [
        (ROOT / "backend", ["*.py"]),
        (ROOT / "frontend" / "src", ["*.ts", "*.tsx"]),
    ]:
        for pat in patterns:
            for p in base.rglob(pat):
                s = str(p)
                if "/tests/" in s or s.endswith(".test.ts") or s.endswith(".test.tsx"):
                    continue
                if "__pycache__" in s or "node_modules" in s or ".coverage" in s:
                    continue
                files.append(p)
    return files


def test_no_personal_identifiers_in_shipped_source():
    offenders = []
    for f in _shipped_files():
        text = f.read_text(errors="ignore").lower()
        for ident in IDENTIFIERS:
            if ident in text:
                offenders.append(f"{f.relative_to(ROOT)} :: {ident!r}")
    assert not offenders, "personal identifiers in shipped source:\n" + "\n".join(offenders)


def test_seeded_profile_corpus_is_gitignored():
    gitignore = (ROOT / ".gitignore").read_text()
    assert ".static_files/" in gitignore  # the seeded dev corpus stays out of the repo
