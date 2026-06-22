"""TDD for the prompt version registry (Phase 11.2).

Reuses the existing PromptVersion table; governs versioning, the active pointer,
rollback, and immutability.
"""
import pytest

from backend.services.prompts.registry import PromptImmutableError, PromptRegistry


def test_deploy_creates_v1_active(test_session):
    reg = PromptRegistry(test_session)
    row = reg.deploy("resume", "system: hi")
    assert row.version == "v1"
    assert row.is_active is True
    assert reg.active("resume").version == "v1"


def test_second_deploy_creates_v2_and_switches_active(test_session):
    reg = PromptRegistry(test_session)
    reg.deploy("resume", "system: one")
    v2 = reg.deploy("resume", "system: two")
    assert v2.version == "v2"
    assert v2.parent_version == "v1"
    assert reg.active("resume").version == "v2"
    # v1 content unchanged (immutable artifact).
    assert reg.get("resume", "v1").content_yaml == "system: one"


def test_rollback_switches_active_pointer(test_session):
    reg = PromptRegistry(test_session)
    reg.deploy("resume", "system: one")
    reg.deploy("resume", "system: two")
    reg.rollback("resume", "v1")
    assert reg.active("resume").version == "v1"


def test_deploy_explicit_existing_version_raises(test_session):
    reg = PromptRegistry(test_session)
    reg.deploy("resume", "system: one")
    with pytest.raises(PromptImmutableError):
        reg.deploy("resume", "system: overwrite", version="v1")


def test_get_unknown_version_raises(test_session):
    reg = PromptRegistry(test_session)
    reg.deploy("resume", "system: one")
    with pytest.raises(KeyError):
        reg.get("resume", "v99")


def test_rollback_unknown_version_raises(test_session):
    reg = PromptRegistry(test_session)
    reg.deploy("resume", "system: one")
    with pytest.raises(KeyError):
        reg.rollback("resume", "v99")


def test_active_none_when_never_deployed(test_session):
    assert PromptRegistry(test_session).active("never") is None


def test_list_versions_in_order(test_session):
    reg = PromptRegistry(test_session)
    reg.deploy("resume", "a")
    reg.deploy("resume", "b")
    reg.deploy("resume", "c")
    assert reg.list_versions("resume") == ["v1", "v2", "v3"]
