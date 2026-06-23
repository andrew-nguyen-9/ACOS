from __future__ import annotations

import pytest

from backend.services.flywheel.feedback import FeedbackEngine, record_signal


def test_record_signal_persists_row_with_source(test_session):
    engine = FeedbackEngine(test_session)
    sig = engine.record_signal(
        entity_type="template",
        entity_id="software",
        signal_type="ats_score",
        value=72.0,
        source={"table": "metrics", "ids": ["m1"]},
    )
    assert sig.id
    assert sig.entity_type == "template"
    assert sig.value == 72.0
    assert sig.weight == 1.0  # default
    assert sig.tenant_id is None  # nullable until 12.14
    assert sig.source_json == {"table": "metrics", "ids": ["m1"]}


def test_record_signal_rejects_empty_source(test_session):
    """Trap 1: a signal with no traceable source is a bug, not a feature."""
    engine = FeedbackEngine(test_session)
    with pytest.raises(ValueError, match="traceable source"):
        engine.record_signal(
            entity_type="template", entity_id="x",
            signal_type="ats_score", value=1.0, source={"table": "metrics", "ids": []},
        )
    with pytest.raises(ValueError, match="traceable source"):
        engine.record_signal(
            entity_type="template", entity_id="x",
            signal_type="ats_score", value=1.0, source={},
        )


def test_explain_returns_source_record_ids(test_session):
    engine = FeedbackEngine(test_session)
    sig = engine.record_signal(
        entity_type="application", entity_id="app1",
        signal_type="interview", value=0.7,
        source={"table": "outcome_signals", "ids": ["os1"]},
    )
    explained = engine.explain(sig.id)
    assert explained["signal_id"] == sig.id
    assert explained["entity_type"] == "application"
    assert explained["signal_type"] == "interview"
    assert explained["source"] == {"table": "outcome_signals", "ids": ["os1"]}


def test_explain_missing_signal_returns_none(test_session):
    assert FeedbackEngine(test_session).explain("nope") is None


def test_rollup_averages_with_sample_counts(test_session):
    """Trap 3: rollup must surface n so a 1-sample average reads as noise."""
    engine = FeedbackEngine(test_session)
    src = {"table": "metrics", "ids": ["m"]}
    for v in (60.0, 80.0, 100.0):
        engine.record_signal(
            entity_type="template", entity_id="software",
            signal_type="ats_score", value=v, source=src,
        )
    # a different entity with a single sample — n must distinguish it
    engine.record_signal(
        entity_type="template", entity_id="data",
        signal_type="ats_score", value=40.0, source=src,
    )

    agg = {(a["entity_type"], a["entity_id"], a["signal_type"]): a
           for a in engine.rollup()["aggregates"]}

    software = agg[("template", "software", "ats_score")]
    assert software["avg_value"] == 80.0  # (60+80+100)/3
    assert software["n"] == 3

    data = agg[("template", "data", "ats_score")]
    assert data["avg_value"] == 40.0
    assert data["n"] == 1


def test_rollup_is_tenant_scoped(test_session):
    engine = FeedbackEngine(test_session)
    src = {"table": "metrics", "ids": ["m"]}
    engine.record_signal(entity_type="skill", entity_id="python", signal_type="skill_used",
                         value=1.0, source=src, tenant_id="t1")
    engine.record_signal(entity_type="skill", entity_id="rust", signal_type="skill_used",
                         value=1.0, source=src, tenant_id="t2")

    t1 = engine.rollup(tenant_id="t1")["aggregates"]
    assert {a["entity_id"] for a in t1} == {"python"}


def test_module_record_signal_is_thin_wrapper(test_session):
    """Emit hooks call the module-level helper, not the class."""
    sig = record_signal(
        test_session, entity_type="template", entity_id="software",
        signal_type="ats_score", value=55.0, source={"table": "metrics", "ids": ["m1"]},
    )
    assert sig.value == 55.0
