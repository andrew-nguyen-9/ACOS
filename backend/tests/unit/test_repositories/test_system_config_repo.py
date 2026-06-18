import pytest
from backend.repositories.system_config import SystemConfigRepository


@pytest.fixture
def repo(test_session):
    return SystemConfigRepository(test_session)


def test_set_and_get_value(repo):
    repo.set_value("app_version", "0.1.0")
    assert repo.get_value("app_version") == "0.1.0"


def test_get_value_returns_default_when_missing(repo):
    assert repo.get_value("nonexistent", default="fallback") == "fallback"


def test_get_value_returns_none_by_default(repo):
    assert repo.get_value("nonexistent") is None


def test_set_value_updates_existing(repo):
    repo.set_value("model", "qwen3:8b")
    repo.set_value("model", "llama3:8b")
    assert repo.get_value("model") == "llama3:8b"


def test_set_value_stores_description(repo):
    repo.set_value("timeout", "30", description="Request timeout in seconds")
    record = repo.get("timeout")
    assert record is not None
    assert record.description == "Request timeout in seconds"


def test_set_value_updates_description(repo):
    repo.set_value("timeout", "30", description="Old")
    repo.set_value("timeout", "60", description="New")
    record = repo.get("timeout")
    assert record.description == "New"


def test_set_value_preserves_description_when_none(repo):
    repo.set_value("k", "v", description="keep me")
    repo.set_value("k", "v2")
    record = repo.get("k")
    assert record.description == "keep me"
