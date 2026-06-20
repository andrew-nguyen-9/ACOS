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


def main() -> None:
    _configure_paths()
    import uvicorn
    from backend.main import app  # noqa: PLC0415 — deferred to avoid circular imports at bundle time
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="warning")


if __name__ == "__main__":
    main()
