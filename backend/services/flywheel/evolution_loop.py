"""Phase 13.6 — autonomous prompt-proposal loop (ADR-010).

An off-hot-path watcher that reads success signals and, when a prompt
underperforms, auto-proposes a candidate into the 13.4 human review queue. It
**never promotes** — promotion stays an explicit human act (12.13 / ADR-010).

The loop is glue: threshold + queue-write over existing pieces
(``FeedbackEngine.rollup`` for stats, ``PromptEvolutionService.propose`` which runs
the optimization guardrails, ``PromptVersionRepository`` for the active pointer).
"""
from __future__ import annotations

from typing import Callable

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models.signal import Signal
from backend.repositories.optimization import PromptVersionRepository
from backend.services.flywheel.feedback import FeedbackEngine
from backend.services.flywheel.prompt_evolution import PromptEvolutionService
from backend.services.optimization.guardrails import GuardrailViolation

# Signals the watcher consumes (ADR-010 §5): entity_type tags a prompt-performance
# score, entity_id is the prompt name.
_PROMPT_ENTITY = "prompt"

CandidateFn = Callable[[str, str, dict], str | None]


def heuristic_candidate(prompt_name: str, active_content: str, group: dict) -> str | None:
    """Default candidate generator: a deterministic, reviewable nudge.

    ponytail: not an LLM rewrite — 12.13 left content generation manual. This gives
    a human something concrete to trial; swap in an LLM rewriter via candidate_fn
    without touching the never-promote boundary.
    """
    return (
        active_content.rstrip()
        + "\n# auto-proposed: prioritize specific, quantified, interview-relevant output."
    )


class EvolutionLoop:
    def __init__(
        self,
        session: Session,
        *,
        candidate_fn: CandidateFn = heuristic_candidate,
        min_n: int = 5,
        threshold: float = 0.5,
    ) -> None:
        self._session = session
        self._candidate_fn = candidate_fn
        self._min_n = min_n
        self._threshold = threshold
        self._repo = PromptVersionRepository(session)

    def run(self) -> list[dict]:
        """Scan prompt-performance signals; queue candidates for underperformers.

        Returns one dict per queued proposal. Idempotent over a signal window.
        """
        rollup = FeedbackEngine(self._session).rollup()
        proposed: list[dict] = []

        for agg in rollup["aggregates"]:
            if agg["entity_type"] != _PROMPT_ENTITY:
                continue
            if agg["n"] < self._min_n or agg["avg_value"] >= self._threshold:
                continue

            prompt_name = agg["entity_id"]
            active = self._repo.get_active(prompt_name)
            if active is None:  # nothing to trial against / improve
                continue

            signal_ids = self._signal_ids(prompt_name, agg["signal_type"])
            if self._already_proposed(prompt_name, signal_ids):
                continue  # same window already queued — no duplicate

            content = self._candidate_fn(prompt_name, active.content_yaml, agg)
            if content is None:
                continue

            try:
                cand = PromptEvolutionService(self._session).propose(
                    prompt_name,
                    content,
                    signal_ids=signal_ids,
                    rationale=(
                        f"auto: {agg['signal_type']} avg {agg['avg_value']} over "
                        f"{agg['n']} samples is below {self._threshold}"
                    ),
                    expected_impact="raise generation quality / interview conversion",
                )
            except GuardrailViolation:
                continue  # vetoed — never persisted

            proposed.append(
                {"prompt_name": prompt_name, "version": cand.version, "signal_ids": signal_ids}
            )

        return proposed

    def _signal_ids(self, prompt_name: str, signal_type: str) -> list[str]:
        rows = self._session.scalars(
            select(Signal).where(
                Signal.entity_type == _PROMPT_ENTITY,
                Signal.entity_id == prompt_name,
                Signal.signal_type == signal_type,
            )
        ).all()
        return [r.id for r in rows]

    def _already_proposed(self, prompt_name: str, signal_ids: list[str]) -> bool:
        """A candidate already links this exact signal set ⇒ idempotent skip."""
        for v in self._repo.list_for_prompt(prompt_name):
            rationale = v.change_rationale or ""
            if signal_ids and all(sid in rationale for sid in signal_ids):
                return True
        return False
