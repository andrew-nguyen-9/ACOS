"""Phase 12.13 Adaptive Prompt Evolution.

Lets prompts evolve from success signals as VERSIONED, REVERSIBLE, APPROVAL-GATED
proposals — never a silent live mutation (Phase 11 hard rule). A thin orchestration
layer over existing pieces: the 11.2 ``PromptRegistry`` / ``PromptVersion`` table, the
optimization A/B harness, and ``OptimizationLog`` for the audit trail. It extends them
(candidate rows + an approval gate + signal-linked rationale), never replaces.

Invariants:
- A candidate is a NEW inactive version; the active incumbent is never overwritten.
- ``promote`` requires an explicit ``approved_by`` (no autonomous prod change).
- Every transition writes an audit row (who/what/why); ``rollback`` is one call.
- Active-prompt resolution stays an O(1) pointer read (``get_active``).
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from backend.models.optimization import PromptVersion
from backend.repositories.optimization import (
    OptimizationLogRepository,
    PromptVersionRepository,
)
from backend.services.optimization.ab_testing import ABTestingService
from backend.services.optimization.guardrails import validate_proposal

_ENGINES = {"resume", "ats", "rag", "cover_letter", "copilot"}


def _engine_for(prompt_name: str) -> str:
    """Derive the owning engine from the prompt name (``resume/extract_keywords``)."""
    head = prompt_name.split("/", 1)[0]
    return head if head in _ENGINES else "rag"


class PromptEvolutionService:
    def __init__(self, session: Session) -> None:
        self._session = session
        self._repo = PromptVersionRepository(session)
        self._log = OptimizationLogRepository(session)

    def propose(
        self,
        prompt_name: str,
        proposed_content: str,
        *,
        signal_ids: list[str],
        rationale: str,
        expected_impact: str,
        confidence_level: str = "strong_inference",
        risk_level: str = "low",
    ) -> PromptVersion:
        """Create a candidate as a new inactive version; the incumbent is untouched.

        The rationale links the motivating signals (explainability). Runs the existing
        optimization guardrails before persisting.
        """
        if not signal_ids:
            raise ValueError("a proposal must link the signals that motivated it")

        validate_proposal({
            "target_engine": _engine_for(prompt_name),
            "target_parameter": prompt_name,
            "proposed_value": proposed_content,
            "rationale": rationale,
            "expected_impact": expected_impact,
            "confidence_level": confidence_level,
            "risk_level": risk_level,
        })

        existing = self._repo.list_for_prompt(prompt_name)
        active = self._repo.get_active(prompt_name)
        change_rationale = f"{rationale} | signals: {','.join(signal_ids)}"
        return self._repo.create(
            prompt_name=prompt_name,
            version=f"v{len(existing) + 1}",
            content_yaml=proposed_content,
            is_active=False,                       # candidate — never auto-activated
            parent_version=active.version if active else None,
            change_rationale=change_rationale,
        )

    def trial(self, prompt_name: str, candidate_version: str):
        """A/B the candidate against the active incumbent via the existing harness."""
        active = self._repo.get_active(prompt_name)
        if active is None:
            raise ValueError(f"no active version for {prompt_name} to trial against")
        return ABTestingService(self._session).create_prompt_experiment(
            name=f"prompt-evolution:{prompt_name}",
            target_engine=_engine_for(prompt_name),
            prompt_name=prompt_name,
            version_a=active.version,
            version_b=candidate_version,
        )

    def promote(self, prompt_name: str, version: str, *, approved_by: str) -> PromptVersion:
        """Flip the active pointer to ``version`` — requires explicit approval + audit."""
        if not approved_by:
            raise ValueError("promotion requires explicit approval (approved_by)")
        target = self._get_version(prompt_name, version)
        old_active = self._repo.get_active(prompt_name)
        self._repo.activate(target.id)
        self._audit("applied", prompt_name,
                    old_active.version if old_active else None, version, approved_by)
        return target

    def rollback(self, prompt_name: str, *, approved_by: str = "user") -> PromptVersion:
        """Restore the prior active version in one call (audited)."""
        active = self._repo.get_active(prompt_name)
        if active is None or not active.parent_version:
            raise ValueError(f"no prior version to roll back to for {prompt_name}")
        prior = self._get_version(prompt_name, active.parent_version)
        self._repo.activate(prior.id)
        self._audit("reverted", prompt_name, active.version, prior.version, approved_by)
        return prior

    def _get_version(self, prompt_name: str, version: str) -> PromptVersion:
        for row in self._repo.list_for_prompt(prompt_name):
            if row.version == version:
                return row
        raise ValueError(f"{prompt_name} {version} not found")

    def _audit(self, action: str, prompt_name: str,
               old_value: str | None, new_value: str | None, actor: str) -> None:
        self._log.create(
            action=action,
            target_engine=_engine_for(prompt_name),
            target_parameter=prompt_name,
            old_value=old_value,
            new_value=new_value,
            actor=actor,
        )
