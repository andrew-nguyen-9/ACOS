from __future__ import annotations

from sqlalchemy.orm import Session

from backend.models.base import utcnow
from backend.models.optimization import OptimizationProposal, OptimizationLog
from backend.repositories.optimization import (
    OptimizationProposalRepository,
    OptimizationLogRepository,
)
from backend.repositories.system_config import SystemConfigRepository


class ApprovalRequired(Exception):
    pass


class Applier:
    def __init__(self, session: Session) -> None:
        self._session = session
        self._proposals = OptimizationProposalRepository(session)
        self._logs = OptimizationLogRepository(session)
        self._config = SystemConfigRepository(session)

    def _get_pending(self, proposal_id: str) -> OptimizationProposal:
        p = self._proposals.get(proposal_id)
        if p is None:
            raise ValueError(f"Proposal {proposal_id} not found")
        if p.status != "pending":
            raise ValueError(f"Proposal {proposal_id} is not pending (status={p.status})")
        return p

    def approve(self, proposal_id: str) -> OptimizationProposal:
        p = self._get_pending(proposal_id)
        p.status = "approved"
        p.decided_at = utcnow()
        self._session.flush()
        return p

    def reject(self, proposal_id: str) -> OptimizationProposal:
        p = self._get_pending(proposal_id)
        p.status = "rejected"
        p.decided_at = utcnow()
        self._session.flush()
        return p

    def apply(self, proposal_id: str) -> OptimizationLog:
        p = self._proposals.get(proposal_id)
        if p is None:
            raise ValueError(f"Proposal {proposal_id} not found")
        if p.status != "approved":
            raise ApprovalRequired(
                f"Proposal {proposal_id} must be approved before apply (status={p.status})"
            )
        # Block re-apply: refuse if an applied change is currently in effect
        # (an applied log exists with no later revert).
        prior = self._logs.list_for_proposal(p.id)
        applied_count = sum(1 for l in prior if l.action == "applied")
        reverted_count = sum(1 for l in prior if l.action == "reverted")
        if applied_count > reverted_count:
            raise ValueError(f"Proposal {proposal_id} is already applied; revert before re-applying.")
        old_value = self._config.get_value(p.target_parameter)
        self._config.set_value(p.target_parameter, p.proposed_value)
        log = self._logs.create(
            proposal_id=p.id, action="applied",
            target_engine=p.target_engine, target_parameter=p.target_parameter,
            old_value=old_value, new_value=p.proposed_value,
        )
        self._session.flush()
        return log

    def revert(self, proposal_id: str) -> OptimizationLog:
        logs = self._logs.list_for_proposal(proposal_id)
        applied = [l for l in logs if l.action == "applied"]
        reverted = [l for l in logs if l.action == "reverted"]
        if not applied or len(reverted) >= len(applied):
            raise ValueError(f"No applied change to revert for proposal {proposal_id}")
        last = applied[-1]
        current = self._config.get_value(last.target_parameter)
        self._config.set_value(last.target_parameter, last.old_value or "")
        log = self._logs.create(
            proposal_id=proposal_id, action="reverted",
            target_engine=last.target_engine, target_parameter=last.target_parameter,
            old_value=current, new_value=last.old_value,
        )
        p = self._proposals.get(proposal_id)
        if p is not None:
            p.status = "reverted"
        self._session.flush()
        return log
