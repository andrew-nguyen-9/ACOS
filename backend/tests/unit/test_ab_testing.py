# backend/tests/unit/test_ab_testing.py
import pytest
from backend.services.optimization.ab_testing import ABTestingService
from backend.repositories.optimization import ABVariantRepository


def test_create_and_conclude_picks_winner(test_session):
    svc = ABTestingService(test_session)
    exp = svc.create_experiment(
        "Resume A vs B", "resume",
        variant_a={"template": "software"}, variant_b={"template": "modern"},
    )
    test_session.commit()
    variants = {v.label: v for v in ABVariantRepository(test_session).list_for_experiment(exp.id)}
    a, b = variants["A"], variants["B"]

    # A: 1/4 = 0.25 ; B: 3/4 = 0.75 → B wins
    for _ in range(4): svc.record_impression(a.id)
    svc.record_conversion(a.id)
    for _ in range(4): svc.record_impression(b.id)
    for _ in range(3): svc.record_conversion(b.id)
    test_session.commit()

    assert abs(svc.conversion_rate(a.id) - 0.25) < 1e-9
    assert abs(svc.conversion_rate(b.id) - 0.75) < 1e-9

    concluded = svc.conclude(exp.id); test_session.commit()
    assert concluded.status == "concluded"
    assert concluded.winner_variant_id == b.id


def test_conclude_requires_data(test_session):
    svc = ABTestingService(test_session)
    exp = svc.create_experiment("x", "ats", {"f": 1}, {"f": 2})
    test_session.commit()
    with pytest.raises(ValueError):
        svc.conclude(exp.id)        # no impressions yet


def test_record_unknown_variant_raises(test_session):
    svc = ABTestingService(test_session)
    with pytest.raises(ValueError):
        svc.record_impression("does-not-exist")
    with pytest.raises(ValueError):
        svc.record_conversion("does-not-exist")


def test_conversion_rate_zero_impressions(test_session):
    svc = ABTestingService(test_session)
    exp = svc.create_experiment("x", "resume", {"a": 1}, {"b": 2})
    test_session.commit()
    v = ABVariantRepository(test_session).list_for_experiment(exp.id)[0]
    assert svc.conversion_rate(v.id) == 0.0          # no impressions, no ZeroDivisionError


def test_conclude_tie_breaks_to_variant_a(test_session):
    svc = ABTestingService(test_session)
    exp = svc.create_experiment("tie", "ats", {"a": 1}, {"b": 2})
    test_session.commit()
    variants = {v.label: v for v in ABVariantRepository(test_session).list_for_experiment(exp.id)}
    a, b = variants["A"], variants["B"]
    # Both 1/2 = 0.5 → tie → A wins
    for _ in range(2): svc.record_impression(a.id)
    svc.record_conversion(a.id)
    for _ in range(2): svc.record_impression(b.id)
    svc.record_conversion(b.id)
    test_session.commit()
    concluded = svc.conclude(exp.id); test_session.commit()
    assert concluded.winner_variant_id == a.id       # tie resolves to variant A
