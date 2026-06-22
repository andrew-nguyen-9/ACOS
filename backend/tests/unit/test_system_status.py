"""TDD for the aggregated SystemStatus surface (Phase 11.1)."""
from unittest.mock import MagicMock

from backend.models.system_config import SystemConfig
from backend.services.system_status import collect


def _chroma(ok=True):
    c = MagicMock()
    c.health_check.return_value = ok
    return c


def _ollama(ok=True):
    o = MagicMock()
    o.is_available.return_value = ok
    return o


def test_all_ok(test_session):
    test_session.add(SystemConfig(key="embedding_model", value="nomic-embed-text"))
    test_session.flush()
    status = collect(test_session, _chroma(True), _ollama(True), "nomic-embed-text")
    assert status.db == "ok"
    assert status.chroma == "ok"
    assert status.ollama == "ok"
    assert status.embedding == "ok"
    assert status.overall == "ok"


def test_chroma_down_makes_overall_down(test_session):
    test_session.add(SystemConfig(key="embedding_model", value="nomic-embed-text"))
    test_session.flush()
    status = collect(test_session, _chroma(False), _ollama(True), "nomic-embed-text")
    assert status.chroma == "down"
    assert status.overall == "down"


def test_ollama_down_makes_overall_down(test_session):
    status = collect(test_session, _chroma(True), _ollama(False), "nomic-embed-text")
    assert status.ollama == "down"
    assert status.overall == "down"


def test_stale_embedding_is_degraded(test_session):
    test_session.add(SystemConfig(key="embedding_model", value="old-model"))
    test_session.flush()
    status = collect(test_session, _chroma(True), _ollama(True), "nomic-embed-text")
    assert status.embedding == "degraded"
    assert status.overall == "degraded"


def test_as_dict_includes_overall(test_session):
    test_session.add(SystemConfig(key="embedding_model", value="nomic-embed-text"))
    test_session.flush()
    d = collect(test_session, _chroma(True), _ollama(True), "nomic-embed-text").as_dict()
    assert d["overall"] == "ok"
    assert set(d) >= {"db", "chroma", "ollama", "embedding", "overall"}
