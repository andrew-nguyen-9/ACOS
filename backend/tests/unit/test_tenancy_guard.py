"""Phase 12.14 central tenant guard — the whole point: a missing tenant filter is
a HARD ERROR, not a silent full-table read.
"""
from __future__ import annotations

import pytest

from backend.repositories.experience import ExperienceRepository
from backend.repositories.system_config import SystemConfigRepository
from backend.services.tenancy import (
    DEFAULT_TENANT_ID,
    TenantScopeError,
    ensure_tenant,
    set_session_tenant,
)

_EXP = dict(title="Eng", company="Acme", employment_type="full_time", start_date="2020-01")


def test_scoped_read_without_tenant_raises(test_session):
    test_session.info.pop("tenant_id", None)
    with pytest.raises(TenantScopeError):
        ExperienceRepository(test_session).list()


def test_scoped_create_without_tenant_raises(test_session):
    test_session.info.pop("tenant_id", None)
    with pytest.raises(TenantScopeError):
        ExperienceRepository(test_session).create(**_EXP)


def test_create_auto_injects_current_tenant(test_session):
    ensure_tenant(test_session, DEFAULT_TENANT_ID)
    set_session_tenant(test_session, DEFAULT_TENANT_ID)
    exp = ExperienceRepository(test_session).create(**_EXP)
    assert exp.tenant_id == DEFAULT_TENANT_ID


def test_list_filters_to_current_tenant(test_session):
    ensure_tenant(test_session, "t1")
    ensure_tenant(test_session, "t2")
    set_session_tenant(test_session, "t1")
    e1 = ExperienceRepository(test_session).create(**_EXP)
    set_session_tenant(test_session, "t2")
    e2 = ExperienceRepository(test_session).create(**_EXP)

    set_session_tenant(test_session, "t1")
    ids = {e.id for e in ExperienceRepository(test_session).list()}
    assert e1.id in ids
    assert e2.id not in ids


def test_get_cross_tenant_returns_none(test_session):
    """A row owned by another tenant resolves to None, never the row."""
    ensure_tenant(test_session, "t1")
    ensure_tenant(test_session, "t2")
    set_session_tenant(test_session, "t1")
    e1 = ExperienceRepository(test_session).create(**_EXP)
    set_session_tenant(test_session, "t2")
    assert ExperienceRepository(test_session).get(e1.id) is None


def test_count_is_tenant_scoped(test_session):
    ensure_tenant(test_session, "t1")
    ensure_tenant(test_session, "t2")
    set_session_tenant(test_session, "t1")
    ExperienceRepository(test_session).create(**_EXP)
    ExperienceRepository(test_session).create(**_EXP)
    set_session_tenant(test_session, "t2")
    ExperienceRepository(test_session).create(**_EXP)
    set_session_tenant(test_session, "t1")
    assert ExperienceRepository(test_session).count() == 2


def test_shared_model_needs_no_tenant(test_session):
    """SystemConfig is shared (code/config) — querying it without a tenant must not raise."""
    test_session.info.pop("tenant_id", None)
    SystemConfigRepository(test_session).list()  # no raise
