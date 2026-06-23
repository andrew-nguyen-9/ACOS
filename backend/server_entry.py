"""PyInstaller entry point. Wraps uvicorn so the backend runs as a standalone binary."""
from __future__ import annotations

import os
import sys


def _configure_paths() -> None:
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        data_dir = os.path.join(os.path.expanduser("~"), ".acos")
        os.makedirs(data_dir, exist_ok=True)
        os.environ.setdefault("ACOS_DB_PATH", os.path.join(data_dir, "acos.db"))
        os.environ.setdefault("ACOS_CHROMA_PATH", os.path.join(data_dir, "chroma"))


def install_uvloop() -> None:
    """Install uvloop as the asyncio event-loop policy (12.2).

    uvicorn[standard] already prefers uvloop, but installing it at the entry
    point makes the fast loop the policy for any loop spawned before uvicorn
    boots and lets us assert it in tests.
    """
    import uvloop  # noqa: PLC0415 — kept off module import for cold-start budget

    uvloop.install()


def main() -> None:
    _configure_paths()
    install_uvloop()
    import uvicorn
    from backend.main import app  # noqa: PLC0415 — deferred to avoid circular imports at bundle time
    # workers=1: single process — the sidecar is one local user, and extra workers
    # would duplicate the resident memory (Chroma/model state) for no throughput
    # gain. loop="uvloop": uvicorn runs its loop on uvloop. install_uvloop() above
    # already set uvloop as the asyncio *policy* (12.2, unit-tested) so any loop
    # spawned before uvicorn boots is fast too. Both are idempotent and both fail
    # loudly if uvloop is ever stripped from a build — kept explicit on purpose, not
    # duplicated work (uvicorn would select uvloop under loop="auto" regardless).
    uvicorn.run(app, host="127.0.0.1", port=8000, workers=1, loop="uvloop", log_level="warning")


if __name__ == "__main__":
    main()
