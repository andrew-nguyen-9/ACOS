"""TDD for the observability metrics store (Phase 11.2)."""
import pytest

from backend.services.observability.metrics import MetricsStore


def test_record_returns_row_with_meta_roundtrip(test_session):
    store = MetricsStore(test_session)
    row = store.record("ats_score", 82.0, {"resume_id": "abc"})
    assert row.kind == "ats_score"
    assert row.value == 82.0
    assert row.meta_json == {"resume_id": "abc"}


def test_series_returns_values_in_insertion_order(test_session):
    store = MetricsStore(test_session)
    for v in (70.0, 75.0, 80.0):
        store.record("ats_score", v)
    series = store.series("ats_score")
    assert [m.value for m in series] == [70.0, 75.0, 80.0]


def test_series_filters_by_kind(test_session):
    store = MetricsStore(test_session)
    store.record("ats_score", 80.0)
    store.record("retrieval_quality", 0.9)
    assert len(store.series("ats_score")) == 1
    assert store.series("ats_score")[0].value == 80.0


def test_rolling_averages_last_window(test_session):
    store = MetricsStore(test_session)
    for v in (10.0, 20.0, 30.0, 40.0):
        store.record("ats_score", v)
    # last 2 → (30+40)/2 = 35
    assert store.rolling("ats_score", window=2) == 35.0


def test_rolling_empty_returns_none(test_session):
    store = MetricsStore(test_session)
    assert store.rolling("ats_score", window=5) is None


def test_record_rejects_unknown_kind(test_session):
    store = MetricsStore(test_session)
    with pytest.raises(ValueError):
        store.record("not_a_real_kind", 1.0)
