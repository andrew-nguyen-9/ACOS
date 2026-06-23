"""Phase 14.1 — /health/version (versioning spine) + single-source guard.

The version endpoint is the one place that answers "what exactly is this build":
app semver + model + active prompt-versions + migration head. Reproducibility
(the determinism tests) is meaningless unless this tuple is pinnable.
"""
from __future__ import annotations

import json
from pathlib import Path

from backend.config import get_settings
from backend.models.optimization import PromptVersion

_REPO = Path(__file__).resolve().parents[3]


def test_version_endpoint_returns_all_four_fields(client):
    r = client.get("/api/v1/health/version")
    assert r.status_code == 200
    body = r.json()
    assert body["app_version"] == get_settings().app_version
    # model field carries generator + embedder tags (the model "version")
    assert body["model"]["generator"] == get_settings().default_model
    assert body["model"]["embedder"] == get_settings().embedding_model
    assert "prompt_versions" in body and isinstance(body["prompt_versions"], list)
    assert isinstance(body["migration_head"], str) and body["migration_head"]


def test_version_endpoint_migration_head_matches_alembic(client):
    """migration_head must equal the alembic *script-directory* head.

    The app provisions schema via Base.metadata.create_all (database.py), so the
    DB's alembic_version is not stamped — the meaningful number is the head the
    code defines, computed from the migration scripts.
    """
    from alembic.config import Config
    from alembic.script import ScriptDirectory

    cfg = Config(str(_REPO / "alembic.ini"))
    head = ScriptDirectory.from_config(cfg).get_current_head()

    r = client.get("/api/v1/health/version")
    assert r.json()["migration_head"] == head


def test_version_endpoint_lists_active_prompts(client, test_session):
    test_session.add(
        PromptVersion(
            prompt_name="resume/generate",
            version="2.0",
            content_yaml="system: x",
            is_active=True,
        )
    )
    test_session.add(
        PromptVersion(
            prompt_name="resume/generate",
            version="1.0",
            content_yaml="system: old",
            is_active=False,  # inactive — must NOT appear
        )
    )
    test_session.commit()

    r = client.get("/api/v1/health/version")
    active = r.json()["prompt_versions"]
    assert {"prompt_name": "resume/generate", "version": "2.0"} in active
    assert all(p["version"] != "1.0" for p in active)


def test_app_version_single_source():
    """Trap #3: one home for app semver. tauri.conf.json is canonical (it ships
    in the DMG/updater); config.app_version mirrors it. This guard fails the
    suite if they drift — there is no second place to silently update.
    """
    tauri = json.loads(
        (_REPO / "frontend" / "src-tauri" / "tauri.conf.json").read_text()
    )
    assert tauri["version"] == get_settings().app_version
