"""Phase 12.13 — A/B trial of a candidate prompt vs the incumbent, then promotion."""
from __future__ import annotations

from backend.services.optimization.ab_testing import ABTestingService
from backend.services.prompts.registry import PromptRegistry
from backend.services.flywheel.prompt_evolution import PromptEvolutionService


def _setup(session):
    PromptRegistry(session).deploy("resume/extract_keywords", "system: v1", version="v1")
    svc = PromptEvolutionService(session)
    svc.propose("resume/extract_keywords", "system: v2", signal_ids=["s1"],
                rationale="v1 underperforms", expected_impact="raise interview rate")
    return svc


def test_trial_creates_ab_experiment_and_records_results(test_session):
    svc = _setup(test_session)
    exp = svc.trial("resume/extract_keywords", "v2")

    ab = ABTestingService(test_session)
    comp = ab.comparison(exp.id)
    versions = {v["version"] for v in comp["variants"]}
    assert versions == {"v1", "v2"}                      # incumbent vs candidate

    # results record through the existing A/B harness
    cand = next(v for v in comp["variants"] if v["version"] == "v2")
    ab.record_impression(cand["id"])
    ab.record_conversion(cand["id"])
    assert ab.conversion_rate(cand["id"]) == 1.0


def test_promote_after_trial_flips_active(test_session):
    svc = _setup(test_session)
    svc.trial("resume/extract_keywords", "v2")
    svc.promote("resume/extract_keywords", "v2", approved_by="andrew")
    assert PromptRegistry(test_session).active("resume/extract_keywords").version == "v2"
