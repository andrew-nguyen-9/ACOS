"""Phase 16.6 (ADR-018) — capability-manifest permission model, default-closed."""
from __future__ import annotations

import pytest

from backend.models.audit import AuditLog
from backend.security import permissions
from backend.security.permissions import PermissionDenied, PermissionManifest


def test_in_manifest_access_passes():
    permissions.require("optimization", resource="signals", action="optimization")
    # no raise


def test_unlisted_resource_denied():
    with pytest.raises(PermissionDenied):
        permissions.require("optimization", resource="resumes")  # not in manifest


def test_unlisted_action_denied():
    with pytest.raises(PermissionDenied):
        permissions.require("flywheel", action="delete_everything")


def test_unregistered_module_denied():
    # Default-closed: a module with no manifest gets nothing.
    with pytest.raises(PermissionDenied):
        permissions.require("rogue_module", resource="signals")


def test_denial_is_audited(test_session):
    with pytest.raises(PermissionDenied):
        permissions.require("optimization", resource="resumes", session=test_session)
    rows = test_session.query(AuditLog).filter(AuditLog.op_type == "permission").all()
    assert len(rows) == 1
    assert "data_access:resumes" in rows[0].metadata_json


def test_empty_manifest_denies_all():
    permissions.register(PermissionManifest(name="empty"))
    with pytest.raises(PermissionDenied):
        permissions.require("empty", resource="anything")
    with pytest.raises(PermissionDenied):
        permissions.require("empty", action="anything")


def test_route_enforces_manifest(client, test_session):
    """The optimization route runs under its manifest (in-manifest → 200)."""
    r = client.post("/api/v1/optimization/proposals/generate")
    assert r.status_code == 200
