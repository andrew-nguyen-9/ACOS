"""Phase 13.6 — autonomous prompt-proposal loop (ADR-010: propose-only, never promote)."""
from __future__ import annotations

from unittest.mock import patch

from backend.repositories.optimization import PromptVersionRepository
from backend.services.flywheel.evolution_loop import EvolutionLoop
from backend.services.flywheel.feedback import FeedbackEngine
from backend.services.optimization.guardrails import GuardrailViolation
from backend.services.prompts.registry import PromptRegistry

PROMPT = "resume/extract_keywords"


def _incumbent(session) -> None:
    PromptRegistry(session).deploy(PROMPT, "system: extract the keywords", version="v1")


def _underperforming_signals(session, n: int = 6, value: float = 0.2) -> list[str]:
    eng = FeedbackEngine(session)
    ids = []
    for i in range(n):
        sig = eng.record_signal(
            entity_type="prompt", entity_id=PROMPT, signal_type="prompt_quality",
            value=value, source={"table": "generations", "ids": [f"g{i}"]},
        )
        ids.append(sig.id)
    session.flush()
    return ids


def test_threshold_met_queues_exactly_one_linked_proposal(test_session):
    _incumbent(test_session)
    sig_ids = _underperforming_signals(test_session)

    proposals = EvolutionLoop(test_session).run()

    assert len(proposals) == 1
    p = proposals[0]
    assert p["prompt_name"] == PROMPT
    # the proposal links its triggering signals (explainable)
    cands = PromptVersionRepository(test_session).list_for_prompt(PROMPT)
    cand = next(c for c in cands if not c.is_active)
    assert all(sid in cand.change_rationale for sid in sig_ids)


def test_below_threshold_proposes_nothing(test_session):
    """n < min_n: a 1-sample average is noise, not evidence."""
    _incumbent(test_session)
    _underperforming_signals(test_session, n=2)
    assert EvolutionLoop(test_session).run() == []


def test_healthy_prompt_proposes_nothing(test_session):
    _incumbent(test_session)
    _underperforming_signals(test_session, n=6, value=0.95)  # performing well
    assert EvolutionLoop(test_session).run() == []


def test_loop_never_promotes(test_session):
    """The whole boundary: the loop has no promotion path."""
    _incumbent(test_session)
    _underperforming_signals(test_session)

    with patch.object(__import__("backend.services.flywheel.prompt_evolution",
                                 fromlist=["PromptEvolutionService"]).PromptEvolutionService,
                       "promote") as promote:
        EvolutionLoop(test_session).run()
        promote.assert_not_called()

    # active pointer is unchanged — the incumbent still serves
    assert PromptVersionRepository(test_session).get_active(PROMPT).version == "v1"


def test_guardrail_veto_suppresses_proposal(test_session):
    _incumbent(test_session)
    _underperforming_signals(test_session)

    with patch("backend.services.flywheel.evolution_loop.PromptEvolutionService.propose",
               side_effect=GuardrailViolation("vetoed")):
        proposals = EvolutionLoop(test_session).run()

    assert proposals == []
    # nothing persisted beyond the incumbent
    assert len(PromptVersionRepository(test_session).list_for_prompt(PROMPT)) == 1


def test_no_active_version_proposes_nothing(test_session):
    """Nothing to improve / trial against when the prompt has no active version."""
    _underperforming_signals(test_session)  # signals but no incumbent deployed
    assert EvolutionLoop(test_session).run() == []


def test_candidate_fn_returning_none_skips(test_session):
    _incumbent(test_session)
    _underperforming_signals(test_session)
    loop = EvolutionLoop(test_session, candidate_fn=lambda *_: None)
    assert loop.run() == []


def test_idempotent_same_window_no_duplicate(test_session):
    _incumbent(test_session)
    _underperforming_signals(test_session)

    first = EvolutionLoop(test_session).run()
    second = EvolutionLoop(test_session).run()

    assert len(first) == 1
    assert second == []  # same signal window → no duplicate candidate
    assert len(PromptVersionRepository(test_session).list_for_prompt(PROMPT)) == 2  # v1 + one candidate
