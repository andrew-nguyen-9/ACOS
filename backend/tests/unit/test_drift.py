"""TDD for drift detection (Phase 11.2)."""
from unittest.mock import MagicMock

from backend.services.observability.drift import (
    DriftDetector,
    compute_embedding_drift,
)
from backend.services.observability.metrics import MetricsStore


def test_flat_series_not_drifting(test_session):
    store = MetricsStore(test_session)
    for _ in range(6):
        store.record("ats_score", 80.0)
    report = {r["kind"]: r for r in DriftDetector(test_session).report(window=3)}
    ats = report["ats_score"]
    assert ats["drifting"] is False
    assert ats["delta"] == 0.0


def test_jump_beyond_threshold_is_drifting(test_session):
    store = MetricsStore(test_session)
    for _ in range(3):
        store.record("ats_score", 80.0)
    for _ in range(3):
        store.record("ats_score", 40.0)  # large drop
    report = {r["kind"]: r for r in DriftDetector(test_session).report(window=3)}
    ats = report["ats_score"]
    assert ats["drifting"] is True
    assert ats["delta"] < 0


def test_insufficient_data_not_drifting(test_session):
    report = {r["kind"]: r for r in DriftDetector(test_session).report()}
    # No samples recorded → every kind present, none drifting.
    assert report["ats_score"]["drifting"] is False
    assert report["ats_score"]["baseline"] is None


def test_threshold_overridable_via_system_config(test_session):
    from backend.models.system_config import SystemConfig

    test_session.add(SystemConfig(key="drift_threshold::ats_score", value="100"))
    store = MetricsStore(test_session)
    for _ in range(3):
        store.record("ats_score", 80.0)
    for _ in range(3):
        store.record("ats_score", 40.0)
    report = {r["kind"]: r for r in DriftDetector(test_session).report(window=3)}
    # delta is -40, threshold raised to 100 → not drifting.
    assert report["ats_score"]["drifting"] is False


def test_compute_embedding_drift_identical_is_zero():
    embedder = MagicMock()
    embedder.embed.side_effect = lambda t: [1.0, 0.0, 0.0]
    drift = compute_embedding_drift(["a"], embedder, [[1.0, 0.0, 0.0]])
    assert abs(drift) < 1e-9


def test_compute_embedding_drift_orthogonal_is_one():
    embedder = MagicMock()
    embedder.embed.side_effect = lambda t: [1.0, 0.0, 0.0]
    drift = compute_embedding_drift(["a"], embedder, [[0.0, 1.0, 0.0]])
    assert abs(drift - 1.0) < 1e-9
