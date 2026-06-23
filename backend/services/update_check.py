"""Phase 18.5 (ADR-020, honoring ADR-011) — in-app update *check*.

Compares the local version against a version manifest and reports whether a newer
version exists. It **only notifies** — it never downloads or installs anything
(no silent/forced update). The manifest source is pluggable: a static file for
alpha, GitHub Releases later (Q12). Data-free: only a version string is compared;
nothing about the user crosses the wire (ADR-011).

This module does ZERO network I/O itself — the caller passes the already-fetched
manifest dict. That keeps the policy (compare + notify) testable and the single
network touch (fetching the manifest) isolated to the caller / FE updater.
"""
from __future__ import annotations

from dataclasses import dataclass


def _parse(v: str) -> tuple[int, ...]:
    parts = []
    for chunk in v.strip().lstrip("v").split("."):
        num = "".join(c for c in chunk if c.isdigit())
        parts.append(int(num) if num else 0)
    return tuple(parts)


@dataclass(frozen=True)
class UpdateStatus:
    update_available: bool
    local_version: str
    latest_version: str
    download_url: str | None  # for the user to click — never auto-fetched


def check(local_version: str, manifest: dict) -> UpdateStatus:
    """Pure compare. ``manifest`` = {"version": "x.y.z", "url": "..."} (GitHub
    Releases or a static file — same shape). Returns notify-only status."""
    latest = str(manifest.get("version", local_version))
    available = _parse(latest) > _parse(local_version)
    return UpdateStatus(
        update_available=available,
        local_version=local_version,
        latest_version=latest,
        download_url=manifest.get("url") if available else None,
    )
