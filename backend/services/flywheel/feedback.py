"""Phase 12.10 local feedback-loop engine.

Turns raw outcome events (resume sent, ATS score, interview result, skill used)
into normalized, source-linked ``signals`` the 12.11 ROI engine and 12.13 prompt
evolution consume. Descriptive stats only — no ML, no cross-user (12.15), no
prompt mutation (12.13).
"""
from __future__ import annotations

from collections import defaultdict

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models.signal import Signal


class FeedbackEngine:
    def __init__(self, session: Session) -> None:
        self._session = session

    def record_signal(
        self,
        *,
        entity_type: str,
        entity_id: str,
        signal_type: str,
        value: float,
        source: dict,
        weight: float = 1.0,
        tenant_id: str | None = None,  # nullable until 12.14
    ) -> Signal:
        # Trap 1: every signal must trace to source record ids; refuse orphans.
        if not source or not source.get("ids"):
            raise ValueError(
                "signal requires a traceable source: {'table': ..., 'ids': [...]}"
            )
        # 12.14: signals are tenant-scoped (NOT NULL). Default to the session's active
        # tenant when an emit hook didn't pass one — Signal bypasses BaseRepository.
        if tenant_id is None:
            from backend.services.tenancy import require_session_tenant

            tenant_id = require_session_tenant(self._session)
        sig = Signal(
            tenant_id=tenant_id,
            entity_type=entity_type,
            entity_id=entity_id,
            signal_type=signal_type,
            value=float(value),
            weight=float(weight),
            source_json=source,
        )
        self._session.add(sig)
        self._session.flush()
        return sig

    def explain(self, signal_id: str) -> dict | None:
        """Return the signal's source record ids — no orphan/hallucinated signals."""
        sig = self._session.get(Signal, signal_id)
        if sig is None:
            return None
        return {
            "signal_id": sig.id,
            "entity_type": sig.entity_type,
            "entity_id": sig.entity_id,
            "signal_type": sig.signal_type,
            "value": sig.value,
            "weight": sig.weight,
            "source": sig.source_json,
        }

    def rollup(self, tenant_id: str | None = None) -> dict:
        """Per-entity descriptive aggregates with sample counts.

        Grouped by (entity_type, entity_id, signal_type): avg value, avg weight,
        and ``n`` so a 1-sample average reads as noise (Trap 3). ``tenant_id=None``
        means all rows — the single-tenant world until 12.14 scopes reads.

        # ponytail: computed on demand. A few hundred signal rows = sub-ms in
        # Python; materialize a rollup cache only if this shows up in a profile.
        """
        stmt = select(Signal)
        if tenant_id is not None:
            stmt = stmt.where(Signal.tenant_id == tenant_id)
        rows = self._session.scalars(stmt).all()

        groups: dict[tuple[str, str, str], list[Signal]] = defaultdict(list)
        for s in rows:
            groups[(s.entity_type, s.entity_id, s.signal_type)].append(s)

        aggregates = [
            {
                "entity_type": etype,
                "entity_id": eid,
                "signal_type": stype,
                "avg_value": round(sum(s.value for s in members) / len(members), 4),
                "avg_weight": round(sum(s.weight for s in members) / len(members), 4),
                "n": len(members),
            }
            for (etype, eid, stype), members in groups.items()
        ]
        aggregates.sort(key=lambda a: (a["entity_type"], a["entity_id"], a["signal_type"]))
        return {"tenant_id": tenant_id, "aggregates": aggregates}


def record_signal(session: Session, **kwargs: object) -> Signal:
    """Thin emit helper for write-path hooks — keeps call sites one-liners."""
    return FeedbackEngine(session).record_signal(**kwargs)  # type: ignore[arg-type]
