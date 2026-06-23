# Phase 8: Controlled Autonomous Optimization System — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a closed-loop, human-gated optimization system that learns from real application outcomes and proposes (never auto-applies) explainable, reversible improvements to the resume, ATS, RAG, cover-letter, and copilot engines.

**Architecture:** Outcome data already captured in `outcome_signals` (Phase 6) feeds an **Evaluator** that computes effectiveness metrics. A **Recommender** turns those metrics into `OptimizationProposal` rows, each carrying full explainability (what / why / expected impact / confidence / risk). Proposals stay `pending` until a human approves them via the UI; only then does the **Applier** mutate the target (a `system_config` value or a new `PromptVersion`) and write an immutable `OptimizationLog` audit entry. Every applied change is reversible by replaying the log in reverse. A/B experiments run two variants side-by-side and are scored on **interview conversion rate**, never ATS score alone. A learning-loop orchestrator fires after every N applications to refresh embeddings, recalibrate rankings, and regenerate proposals.

**Tech Stack:** Python 3.11+, FastAPI, SQLAlchemy 2.0, Pydantic v2, Alembic, SQLite, ChromaDB, Ollama; React 18 + TypeScript + TailwindCSS (Tauri v2 shell). Tests: pytest (backend), tsc (frontend type-check).

## Global Constraints

- **Human approval gate is mandatory.** No optimization is ever applied to production config or prompts without an explicit user approval action. The Applier service must refuse to act on a proposal whose `status != "approved"`.
- **Every change is logged.** Each apply/revert writes an immutable `OptimizationLog` row (append-only; never updated or deleted).
- **Every change is reversible.** Each applied change records its `old_value`, enabling a one-call revert.
- **Every proposal is explainable.** A proposal is invalid unless it has non-empty `rationale`, `expected_impact`, `confidence_level`, and `risk_level`.
- **Confidence levels reuse the ACOS three-level system:** `verified`, `strong_inference`, `weak_inference` (per `docs/adr/ADR-006-evidence-confidence-system.md`). Risk levels: `low`, `medium`, `high`.
- **Primary objective is interview rate, NOT ATS score.** Any proposal whose sole justification is raising ATS score must be rejected by the guardrail validator. "Interview rate" = fraction of applications reaching `phone_screen` or stronger.
- **Strong signals:** `phone_screen`, `interview`, `final_round`, `offer`, `accepted`. **Weak signals:** `applied`/`no_response` (neutral-to-negative). These map to the existing `outcome_signals.signal_type` enum.
- **Prompts are versioned, never overwritten.** A prompt change creates a new `PromptVersion` row; the prior version is retained and can be re-activated.
- **No external APIs.** All computation is local (SQLite + ChromaDB + Ollama). No network calls to third-party services.
- **No model deletion.** The system never deletes prior prompt versions, embeddings, or config history.
- **Learning-loop trigger count** is read from `system_config` key `learning_trigger_count` (default `"5"`), never hardcoded.
- **Naming:** new optimization engine target identifiers are exactly: `resume`, `ats`, `rag`, `cover_letter`, `copilot`.
- **TDD throughout.** Every task writes failing tests first, then minimal implementation, then verifies green, then commits.
- **Type checking:** backend code is fully typed (no bare `Any` without justification); frontend passes `tsc --noEmit`.

## Existing Code This Plan Builds On

- `backend/models/outcome.py` — `OutcomeSignal` (id, application_id, resume_id, signal_type, signal_weight, template_used, ats_score, industry, position_type, created_at). Enum: `no_response, rejected, phone_screen, interview, final_round, offer, accepted`.
- `backend/repositories/outcome.py` — `OutcomeSignalRepository(session)` with `.list()`, `.get_by_application()`, `.get_by_resume()`, `.get_by_signal_type()`.
- `backend/services/learning/ranker.py` — `OutcomeRanker(session)` with `record_outcome(...)`, `get_template_rankings()`, `get_ats_vs_outcome_correlation()`. Signal weights live in `_SIGNAL_WEIGHTS`.
- `backend/api/v1/routes/learning.py` — existing router (no prefix; mounted at `/api/v1`). Has `/learning/outcome`, `/learning/reindex`, `/learning/rankings`, `/learning/report`.
- `backend/models/base.py` — `Base`, `TimestampMixin`, `generate_uuid()` (returns `uuid4().hex`, 32-char), `utcnow()` (ISO string).
- `backend/repositories/base.py` — `BaseRepository[T]` with `.get(id)`, `.list()`, `.create(**kwargs)`, `.delete(id)`, `.count()`. Attribute is `self.session`.
- `backend/repositories/system_config.py` — `SystemConfigRepository(session)` with `.get_value(key, default=None)`, `.set_value(key, value, description=None)`, `.list()`.
- `backend/services/prompt_loader.py` — `PromptLoader().load(name)` reads `backend/prompts/<name>.yaml`, returns `{version, system, user_template}`. Prompts: `resume/generate`, `resume/extract_keywords`, `ats/score_ats`, etc.
- `backend/database.py` — `get_session()` FastAPI dependency, `seed_system_config(session)`, `SessionLocal`, `init_db()`.
- `backend/main.py` — `create_app()`; routers registered with `app.include_router(<router>, prefix="/api/v1")`. Add new routers here.
- `backend/models/__init__.py` — imports every model so `Base.metadata` sees it. New models MUST be added here.
- `database/migrations/versions/ae7ba4bb04de_initial_schema.py` — Alembic baseline (`down_revision = None`). New migrations chain from the latest head.
- Frontend: `frontend/src/services/api.ts` exports `apiFetch<T>(path, init?)` and `ApiError`. `frontend/src/App.tsx` defines routes. `frontend/src/layouts/AppShell.tsx` defines `NAV_ITEMS`. Pages live in `frontend/src/pages/`.

---
### Task 1: OptimizationProposal model + repository

**Files:**
- Create: `backend/models/optimization.py`
- Modify: `backend/models/__init__.py` (register new model)
- Test: `backend/tests/unit/test_optimization_models.py`

**Interfaces:**
- Produces: `OptimizationProposal` ORM model (table `optimization_proposals`) and `OptimizationProposalRepository(session)`.
  - Columns: `id: str` (pk, 32-char uuid), `target_engine: str` (one of `resume|ats|rag|cover_letter|copilot`), `target_parameter: str`, `current_value: str | None`, `proposed_value: str`, `rationale: str`, `expected_impact: str`, `confidence_level: str` (`verified|strong_inference|weak_inference`), `risk_level: str` (`low|medium|high`), `evidence_json: str | None`, `status: str` (`pending|approved|rejected|reverted`, default `pending`), `created_at: str`, `updated_at: str`, `decided_at: str | None`.
  - Repo methods (inherited from `BaseRepository`): `.get`, `.list`, `.create`, `.delete`, `.count`. Add `.list_by_status(status: str) -> list[OptimizationProposal]`.

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/unit/test_optimization_models.py
import pytest
from backend.models.optimization import OptimizationProposal
from backend.repositories.optimization import OptimizationProposalRepository


def test_create_and_fetch_proposal(test_session):
    repo = OptimizationProposalRepository(test_session)
    p = repo.create(
        target_engine="ats",
        target_parameter="ats_keyword_weight",
        current_value="0.35",
        proposed_value="0.40",
        rationale="Keyword-heavy roles correlate with more interviews.",
        expected_impact="+8% interview rate for fintech roles",
        confidence_level="strong_inference",
        risk_level="low",
        evidence_json='{"sample_size": 12}',
    )
    test_session.commit()
    assert p.id and len(p.id) == 32
    assert p.status == "pending"          # default
    assert p.decided_at is None
    fetched = repo.get(p.id)
    assert fetched is not None
    assert fetched.target_engine == "ats"


def test_list_by_status(test_session):
    repo = OptimizationProposalRepository(test_session)
    repo.create(
        target_engine="resume", target_parameter="template", proposed_value="B",
        rationale="r", expected_impact="i", confidence_level="weak_inference",
        risk_level="low",
    )
    approved = repo.create(
        target_engine="rag", target_parameter="similarity_threshold", proposed_value="0.4",
        rationale="r", expected_impact="i", confidence_level="verified", risk_level="medium",
        status="approved",
    )
    test_session.commit()
    pending = repo.list_by_status("pending")
    assert len(pending) == 1
    assert repo.list_by_status("approved")[0].id == approved.id


def test_invalid_engine_rejected(test_session):
    repo = OptimizationProposalRepository(test_session)
    repo.create(
        target_engine="not_an_engine", target_parameter="x", proposed_value="y",
        rationale="r", expected_impact="i", confidence_level="verified", risk_level="low",
    )
    with pytest.raises(Exception):  # IntegrityError from CheckConstraint
        test_session.commit()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest backend/tests/unit/test_optimization_models.py -v --no-cov`
Expected: FAIL — `ModuleNotFoundError: backend.models.optimization`.

- [ ] **Step 3: Write the model**

```python
# backend/models/optimization.py
from __future__ import annotations

from sqlalchemy import String, Text, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column

from backend.models.base import Base, generate_uuid, utcnow


class OptimizationProposal(Base):
    __tablename__ = "optimization_proposals"
    __table_args__ = (
        CheckConstraint(
            "target_engine IN ('resume','ats','rag','cover_letter','copilot')",
            name="ck_opt_proposal_engine",
        ),
        CheckConstraint(
            "confidence_level IN ('verified','strong_inference','weak_inference')",
            name="ck_opt_proposal_confidence",
        ),
        CheckConstraint(
            "risk_level IN ('low','medium','high')",
            name="ck_opt_proposal_risk",
        ),
        CheckConstraint(
            "status IN ('pending','approved','rejected','reverted')",
            name="ck_opt_proposal_status",
        ),
    )

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=generate_uuid)
    target_engine: Mapped[str] = mapped_column(String(20), nullable=False)
    target_parameter: Mapped[str] = mapped_column(Text, nullable=False)
    current_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    proposed_value: Mapped[str] = mapped_column(Text, nullable=False)
    rationale: Mapped[str] = mapped_column(Text, nullable=False)
    expected_impact: Mapped[str] = mapped_column(Text, nullable=False)
    confidence_level: Mapped[str] = mapped_column(String(20), nullable=False)
    risk_level: Mapped[str] = mapped_column(String(10), nullable=False)
    evidence_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    created_at: Mapped[str] = mapped_column(String(32), default=utcnow)
    updated_at: Mapped[str] = mapped_column(String(32), default=utcnow, onupdate=utcnow)
    decided_at: Mapped[str | None] = mapped_column(String(32), nullable=True)
```

- [ ] **Step 4: Write the repository**

```python
# backend/repositories/optimization.py
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models.optimization import OptimizationProposal
from backend.repositories.base import BaseRepository


class OptimizationProposalRepository(BaseRepository[OptimizationProposal]):
    def __init__(self, session: Session) -> None:
        super().__init__(OptimizationProposal, session)

    def list_by_status(self, status: str) -> list[OptimizationProposal]:
        return list(
            self.session.scalars(
                select(OptimizationProposal).where(OptimizationProposal.status == status)
            ).all()
        )
```

- [ ] **Step 5: Register the model**

In `backend/models/__init__.py`, add after the `OutcomeSignal` import:
```python
from backend.models.optimization import OptimizationProposal
```
And add `"OptimizationProposal"` to the `__all__` list.

- [ ] **Step 6: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest backend/tests/unit/test_optimization_models.py -v --no-cov`
Expected: 3 passed.

- [ ] **Step 7: Commit**

```bash
git add backend/models/optimization.py backend/repositories/optimization.py backend/models/__init__.py backend/tests/unit/test_optimization_models.py
git commit -m "feat(optimization): add OptimizationProposal model and repository"
```

---

### Task 2: OptimizationLog model + repository (append-only audit trail)

**Files:**
- Modify: `backend/models/optimization.py` (add `OptimizationLog`)
- Modify: `backend/models/__init__.py` (register)
- Modify: `backend/repositories/optimization.py` (add `OptimizationLogRepository`)
- Test: `backend/tests/unit/test_optimization_log.py`

**Interfaces:**
- Consumes: `OptimizationProposal` (Task 1) for the `proposal_id` foreign key.
- Produces: `OptimizationLog` ORM model (table `optimization_logs`) and `OptimizationLogRepository(session)`.
  - Columns: `id: str` (pk), `proposal_id: str` (FK → `optimization_proposals.id`, `ondelete=SET NULL`, nullable), `action: str` (`applied|reverted`), `target_engine: str`, `target_parameter: str`, `old_value: str | None`, `new_value: str | None`, `actor: str` (default `"user"`), `created_at: str`.
  - Repo methods: inherited + `.list_for_proposal(proposal_id: str) -> list[OptimizationLog]` and `.list_recent(limit: int = 50) -> list[OptimizationLog]` (ordered by `created_at` desc).
- This table is **append-only**: the repository exposes no update method; `delete` is inherited but MUST NOT be called by application code (audit integrity).

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/unit/test_optimization_log.py
from backend.repositories.optimization import (
    OptimizationProposalRepository,
    OptimizationLogRepository,
)


def _make_proposal(session):
    repo = OptimizationProposalRepository(session)
    p = repo.create(
        target_engine="ats", target_parameter="ats_keyword_weight",
        current_value="0.35", proposed_value="0.40",
        rationale="r", expected_impact="i",
        confidence_level="strong_inference", risk_level="low",
    )
    session.commit()
    return p


def test_log_records_apply(test_session):
    p = _make_proposal(test_session)
    log_repo = OptimizationLogRepository(test_session)
    entry = log_repo.create(
        proposal_id=p.id, action="applied",
        target_engine="ats", target_parameter="ats_keyword_weight",
        old_value="0.35", new_value="0.40",
    )
    test_session.commit()
    assert entry.actor == "user"            # default
    assert log_repo.list_for_proposal(p.id)[0].action == "applied"


def test_list_recent_orders_desc(test_session):
    p = _make_proposal(test_session)
    log_repo = OptimizationLogRepository(test_session)
    log_repo.create(proposal_id=p.id, action="applied",
                    target_engine="ats", target_parameter="w",
                    old_value="1", new_value="2")
    log_repo.create(proposal_id=p.id, action="reverted",
                    target_engine="ats", target_parameter="w",
                    old_value="2", new_value="1")
    test_session.commit()
    recent = log_repo.list_recent(limit=10)
    assert len(recent) == 2
    assert recent[0].action == "reverted"   # most recent first
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest backend/tests/unit/test_optimization_log.py -v --no-cov`
Expected: FAIL — `ImportError: cannot import name 'OptimizationLogRepository'`.

- [ ] **Step 3: Add the model**

Append to `backend/models/optimization.py`:
```python
from sqlalchemy import ForeignKey


class OptimizationLog(Base):
    __tablename__ = "optimization_logs"
    __table_args__ = (
        CheckConstraint(
            "action IN ('applied','reverted')",
            name="ck_opt_log_action",
        ),
    )

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=generate_uuid)
    proposal_id: Mapped[str | None] = mapped_column(
        String(32), ForeignKey("optimization_proposals.id", ondelete="SET NULL"), nullable=True
    )
    action: Mapped[str] = mapped_column(String(10), nullable=False)
    target_engine: Mapped[str] = mapped_column(String(20), nullable=False)
    target_parameter: Mapped[str] = mapped_column(Text, nullable=False)
    old_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    new_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    actor: Mapped[str] = mapped_column(String(40), nullable=False, default="user")
    created_at: Mapped[str] = mapped_column(String(32), default=utcnow)
```
(The `ForeignKey` import may be added to the existing import line at the top instead of a second import statement.)

- [ ] **Step 4: Add the repository**

Append to `backend/repositories/optimization.py`:
```python
from backend.models.optimization import OptimizationLog


class OptimizationLogRepository(BaseRepository[OptimizationLog]):
    def __init__(self, session: Session) -> None:
        super().__init__(OptimizationLog, session)

    def list_for_proposal(self, proposal_id: str) -> list[OptimizationLog]:
        return list(
            self.session.scalars(
                select(OptimizationLog).where(OptimizationLog.proposal_id == proposal_id)
            ).all()
        )

    def list_recent(self, limit: int = 50) -> list[OptimizationLog]:
        return list(
            self.session.scalars(
                select(OptimizationLog)
                .order_by(OptimizationLog.created_at.desc())
                .limit(limit)
            ).all()
        )
```

- [ ] **Step 5: Register the model**

In `backend/models/__init__.py`, extend the optimization import:
```python
from backend.models.optimization import OptimizationProposal, OptimizationLog
```
Add `"OptimizationLog"` to `__all__`.

- [ ] **Step 6: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest backend/tests/unit/test_optimization_log.py backend/tests/unit/test_optimization_models.py -v --no-cov`
Expected: 5 passed.

- [ ] **Step 7: Commit**

```bash
git add backend/models/optimization.py backend/repositories/optimization.py backend/models/__init__.py backend/tests/unit/test_optimization_log.py
git commit -m "feat(optimization): add append-only OptimizationLog audit model and repository"
```

---
### Task 3: PromptVersion model + repository (versioned, reversible prompts)

**Files:**
- Modify: `backend/models/optimization.py` (add `PromptVersion`)
- Modify: `backend/models/__init__.py` (register)
- Modify: `backend/repositories/optimization.py` (add `PromptVersionRepository`)
- Test: `backend/tests/unit/test_prompt_version.py`

**Interfaces:**
- Produces: `PromptVersion` ORM model (table `prompt_versions`) and `PromptVersionRepository(session)`.
  - Columns: `id: str` (pk), `prompt_name: str` (e.g. `"resume/generate"`), `version: str` (e.g. `"1.0"`, `"1.1"`), `content_yaml: str` (full YAML body), `is_active: bool` (default `False`), `parent_version: str | None`, `change_rationale: str | None`, `created_at: str`.
  - Unique constraint on `(prompt_name, version)`.
  - Repo methods: inherited + `.get_active(prompt_name: str) -> PromptVersion | None`, `.list_for_prompt(prompt_name: str) -> list[PromptVersion]`, `.activate(version_id: str) -> PromptVersion` (sets the target row's `is_active=True` and **deactivates all other rows with the same `prompt_name`** — single active version invariant; reversible because prior rows are retained).

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/unit/test_prompt_version.py
import pytest
from backend.repositories.optimization import PromptVersionRepository


def test_activate_enforces_single_active(test_session):
    repo = PromptVersionRepository(test_session)
    v1 = repo.create(prompt_name="resume/generate", version="1.0",
                     content_yaml="system: a", is_active=True)
    v2 = repo.create(prompt_name="resume/generate", version="1.1",
                     content_yaml="system: b", parent_version="1.0",
                     change_rationale="tighter bullet rules")
    test_session.commit()

    repo.activate(v2.id)
    test_session.commit()

    active = repo.get_active("resume/generate")
    assert active is not None and active.version == "1.1"
    # v1 was deactivated, not deleted (reversibility)
    assert repo.get(v1.id).is_active is False
    assert len(repo.list_for_prompt("resume/generate")) == 2


def test_revert_by_reactivating_prior(test_session):
    repo = PromptVersionRepository(test_session)
    v1 = repo.create(prompt_name="ats/score_ats", version="1.0",
                     content_yaml="system: a", is_active=True)
    v2 = repo.create(prompt_name="ats/score_ats", version="1.1",
                     content_yaml="system: b")
    test_session.commit()
    repo.activate(v2.id); test_session.commit()
    repo.activate(v1.id); test_session.commit()   # revert
    assert repo.get_active("ats/score_ats").version == "1.0"


def test_duplicate_version_rejected(test_session):
    repo = PromptVersionRepository(test_session)
    repo.create(prompt_name="ats/score_ats", version="1.0", content_yaml="a")
    repo.create(prompt_name="ats/score_ats", version="1.0", content_yaml="b")
    with pytest.raises(Exception):  # IntegrityError, unique (prompt_name, version)
        test_session.commit()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest backend/tests/unit/test_prompt_version.py -v --no-cov`
Expected: FAIL — `ImportError: cannot import name 'PromptVersionRepository'`.

- [ ] **Step 3: Add the model**

Append to `backend/models/optimization.py`:
```python
from sqlalchemy import Boolean, UniqueConstraint


class PromptVersion(Base):
    __tablename__ = "prompt_versions"
    __table_args__ = (
        UniqueConstraint("prompt_name", "version", name="uq_prompt_name_version"),
    )

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=generate_uuid)
    prompt_name: Mapped[str] = mapped_column(Text, nullable=False)
    version: Mapped[str] = mapped_column(String(20), nullable=False)
    content_yaml: Mapped[str] = mapped_column(Text, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    parent_version: Mapped[str | None] = mapped_column(String(20), nullable=True)
    change_rationale: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[str] = mapped_column(String(32), default=utcnow)
```
(Merge `Boolean, UniqueConstraint` into the existing `from sqlalchemy import ...` line.)

- [ ] **Step 4: Add the repository**

Append to `backend/repositories/optimization.py`:
```python
from backend.models.optimization import PromptVersion


class PromptVersionRepository(BaseRepository[PromptVersion]):
    def __init__(self, session: Session) -> None:
        super().__init__(PromptVersion, session)

    def get_active(self, prompt_name: str) -> PromptVersion | None:
        return self.session.scalars(
            select(PromptVersion).where(
                PromptVersion.prompt_name == prompt_name,
                PromptVersion.is_active.is_(True),
            )
        ).first()

    def list_for_prompt(self, prompt_name: str) -> list[PromptVersion]:
        return list(
            self.session.scalars(
                select(PromptVersion)
                .where(PromptVersion.prompt_name == prompt_name)
                .order_by(PromptVersion.created_at.asc())
            ).all()
        )

    def activate(self, version_id: str) -> PromptVersion:
        target = self.get(version_id)
        if target is None:
            raise ValueError(f"PromptVersion {version_id} not found")
        # Deactivate all siblings, then activate the target (single-active invariant).
        for sibling in self.list_for_prompt(target.prompt_name):
            sibling.is_active = sibling.id == version_id
        self.session.flush()
        return target
```

- [ ] **Step 5: Register the model**

`backend/models/__init__.py`:
```python
from backend.models.optimization import OptimizationProposal, OptimizationLog, PromptVersion
```
Add `"PromptVersion"` to `__all__`.

- [ ] **Step 6: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest backend/tests/unit/test_prompt_version.py -v --no-cov`
Expected: 3 passed.

- [ ] **Step 7: Commit**

```bash
git add backend/models/optimization.py backend/repositories/optimization.py backend/models/__init__.py backend/tests/unit/test_prompt_version.py
git commit -m "feat(optimization): add versioned, reversible PromptVersion model and repository"
```

---

### Task 4: A/B experiment models + Alembic migration

**Files:**
- Modify: `backend/models/optimization.py` (add `ABExperiment`, `ABVariant`)
- Modify: `backend/models/__init__.py` (register both)
- Modify: `backend/repositories/optimization.py` (add `ABExperimentRepository`, `ABVariantRepository`)
- Create: `database/migrations/versions/<rev>_phase8_optimization.py` (Alembic migration for ALL Phase 8 tables)
- Test: `backend/tests/unit/test_ab_models.py`

**Interfaces:**
- Produces:
  - `ABExperiment` (table `ab_experiments`): `id: str` (pk), `name: str`, `target_engine: str` (same engine enum), `metric: str` (default `"interview_conversion_rate"`), `status: str` (`running|concluded`, default `running`), `winner_variant_id: str | None`, `created_at: str`, `concluded_at: str | None`.
  - `ABVariant` (table `ab_variants`): `id: str` (pk), `experiment_id: str` (FK → `ab_experiments.id`, `ondelete=CASCADE`), `label: str` (e.g. `"A"`, `"B"`), `config_json: str`, `impressions: int` (default 0), `conversions: int` (default 0), `created_at: str`.
  - `ABExperimentRepository(session)`: inherited + `.list_running() -> list[ABExperiment]`.
  - `ABVariantRepository(session)`: inherited + `.list_for_experiment(experiment_id: str) -> list[ABVariant]`.

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/unit/test_ab_models.py
from backend.repositories.optimization import (
    ABExperimentRepository, ABVariantRepository,
)


def test_experiment_with_variants(test_session):
    exp_repo = ABExperimentRepository(test_session)
    var_repo = ABVariantRepository(test_session)
    exp = exp_repo.create(name="Resume A vs B", target_engine="resume")
    test_session.commit()
    assert exp.metric == "interview_conversion_rate"   # default
    assert exp.status == "running"

    a = var_repo.create(experiment_id=exp.id, label="A", config_json='{"template":"software"}')
    b = var_repo.create(experiment_id=exp.id, label="B", config_json='{"template":"modern"}')
    test_session.commit()
    assert a.impressions == 0 and a.conversions == 0
    variants = var_repo.list_for_experiment(exp.id)
    assert {v.label for v in variants} == {"A", "B"}


def test_list_running(test_session):
    exp_repo = ABExperimentRepository(test_session)
    exp_repo.create(name="r1", target_engine="ats")
    concluded = exp_repo.create(name="r2", target_engine="rag", status="concluded")
    test_session.commit()
    running = exp_repo.list_running()
    assert len(running) == 1
    assert running[0].name == "r1"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest backend/tests/unit/test_ab_models.py -v --no-cov`
Expected: FAIL — `ImportError`.

- [ ] **Step 3: Add the models**

Append to `backend/models/optimization.py`:
```python
from sqlalchemy import Integer


class ABExperiment(Base):
    __tablename__ = "ab_experiments"
    __table_args__ = (
        CheckConstraint(
            "target_engine IN ('resume','ats','rag','cover_letter','copilot')",
            name="ck_ab_experiment_engine",
        ),
        CheckConstraint("status IN ('running','concluded')", name="ck_ab_experiment_status"),
    )

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=generate_uuid)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    target_engine: Mapped[str] = mapped_column(String(20), nullable=False)
    metric: Mapped[str] = mapped_column(Text, nullable=False, default="interview_conversion_rate")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="running")
    winner_variant_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    created_at: Mapped[str] = mapped_column(String(32), default=utcnow)
    concluded_at: Mapped[str | None] = mapped_column(String(32), nullable=True)


class ABVariant(Base):
    __tablename__ = "ab_variants"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=generate_uuid)
    experiment_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("ab_experiments.id", ondelete="CASCADE"), nullable=False
    )
    label: Mapped[str] = mapped_column(String(20), nullable=False)
    config_json: Mapped[str] = mapped_column(Text, nullable=False)
    impressions: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    conversions: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[str] = mapped_column(String(32), default=utcnow)
```
(Merge `Integer` into the existing `from sqlalchemy import ...` line.)

- [ ] **Step 4: Add the repositories**

Append to `backend/repositories/optimization.py`:
```python
from backend.models.optimization import ABExperiment, ABVariant


class ABExperimentRepository(BaseRepository[ABExperiment]):
    def __init__(self, session: Session) -> None:
        super().__init__(ABExperiment, session)

    def list_running(self) -> list[ABExperiment]:
        return list(
            self.session.scalars(
                select(ABExperiment).where(ABExperiment.status == "running")
            ).all()
        )


class ABVariantRepository(BaseRepository[ABVariant]):
    def __init__(self, session: Session) -> None:
        super().__init__(ABVariant, session)

    def list_for_experiment(self, experiment_id: str) -> list[ABVariant]:
        return list(
            self.session.scalars(
                select(ABVariant).where(ABVariant.experiment_id == experiment_id)
            ).all()
        )
```

- [ ] **Step 5: Register the models**

`backend/models/__init__.py`:
```python
from backend.models.optimization import (
    OptimizationProposal, OptimizationLog, PromptVersion, ABExperiment, ABVariant,
)
```
Add `"ABExperiment"`, `"ABVariant"` to `__all__`.

- [ ] **Step 6: Run model tests to verify green**

Run: `.venv/bin/python -m pytest backend/tests/unit/test_ab_models.py backend/tests/unit/test_optimization_models.py backend/tests/unit/test_optimization_log.py backend/tests/unit/test_prompt_version.py -v --no-cov`
Expected: all passed.

- [ ] **Step 7: Generate the Alembic migration**

Run: `.venv/bin/alembic -c alembic.ini revision --autogenerate -m "phase8 optimization tables"`
This inspects `Base.metadata` (all 5 new tables are now registered) and writes a migration under `database/migrations/versions/`.

- [ ] **Step 8: Verify the migration applies cleanly**

Run: `.venv/bin/alembic -c alembic.ini upgrade head`
Expected: no error; `optimization_proposals`, `optimization_logs`, `prompt_versions`, `ab_experiments`, `ab_variants` created.
Then verify downgrade is reversible: `.venv/bin/alembic -c alembic.ini downgrade -1` then `.venv/bin/alembic -c alembic.ini upgrade head`.
Expected: both succeed.

- [ ] **Step 9: Commit**

```bash
git add backend/models/optimization.py backend/repositories/optimization.py backend/models/__init__.py backend/tests/unit/test_ab_models.py database/migrations/versions/
git commit -m "feat(optimization): add A/B experiment models and Alembic migration for Phase 8 tables"
```

---
### Task 5: Evaluation pipeline service

**Files:**
- Create: `backend/services/optimization/__init__.py` (empty package marker)
- Create: `backend/services/optimization/evaluator.py`
- Test: `backend/tests/unit/test_optimization_evaluator.py`

**Interfaces:**
- Consumes: `OutcomeSignalRepository` (`backend/repositories/outcome.py`), `OutcomeRanker` (`backend/services/learning/ranker.py`), `_SIGNAL_WEIGHTS` keys for strong/weak classification.
- Produces: `Evaluator(session)` with:
  - `interview_rate() -> dict` — `{"interview_rate": float, "total": int, "interviews": int}`. Interview rate = fraction of outcome signals whose `signal_type` is a STRONG signal (`phone_screen`, `interview`, `final_round`, `offer`, `accepted`) over total signals. Returns `0.0` rate when total is 0.
  - `template_effectiveness() -> list[dict]` — wraps `OutcomeRanker.get_template_rankings()` but adds `interview_rate` per template (strong-signal fraction within that template's signals).
  - `ats_outcome_correlation() -> dict` — wraps `OutcomeRanker.get_ats_vs_outcome_correlation()` plus a single Pearson-style `correlation` float between `ats_score` and a binary strong-signal indicator (0/1). Returns `correlation: 0.0` when fewer than 2 data points or zero variance.
  - `industry_effectiveness() -> list[dict]` — per-`industry` strong-signal rate: `[{"industry": str, "interview_rate": float, "sample_size": int}]`.
- Define module constant `STRONG_SIGNALS = {"phone_screen", "interview", "final_round", "offer", "accepted"}` and `WEAK_SIGNALS = {"applied", "no_response", "rejected"}`. (Note: `applied` is not a stored signal_type but is the neutral baseline; `no_response`/`rejected` are the stored weak/negative signals.)

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/unit/test_optimization_evaluator.py
from backend.services.learning.ranker import OutcomeRanker
from backend.services.optimization.evaluator import Evaluator, STRONG_SIGNALS
from backend.repositories.outcome import OutcomeSignalRepository


def _seed(session, rows):
    """rows: list of (signal_type, ats_score, template, industry)."""
    ranker = OutcomeRanker(session)
    # OutcomeRanker.record_outcome requires a real application FK; insert signals directly.
    repo = OutcomeSignalRepository(session)
    from backend.services.learning.ranker import _SIGNAL_WEIGHTS
    # Create a dummy application to satisfy the FK.
    from backend.models.application import Application
    app = Application(company="C", position="P")
    session.add(app); session.flush()
    for st, ats, tpl, ind in rows:
        repo.create(application_id=app.id, signal_type=st,
                    signal_weight=_SIGNAL_WEIGHTS[st], ats_score=ats,
                    template_used=tpl, industry=ind)
    session.commit()


def test_interview_rate(test_session):
    _seed(test_session, [
        ("interview", 80, "A", "fintech"),
        ("no_response", 40, "A", "fintech"),
        ("offer", 90, "B", "ai"),
        ("rejected", 30, "B", "ai"),
    ])
    ev = Evaluator(test_session)
    r = ev.interview_rate()
    assert r["total"] == 4
    assert r["interviews"] == 2           # interview + offer are strong
    assert abs(r["interview_rate"] - 0.5) < 1e-9


def test_template_effectiveness_has_interview_rate(test_session):
    _seed(test_session, [
        ("interview", 80, "A", "fintech"),
        ("no_response", 40, "A", "fintech"),
        ("offer", 90, "B", "ai"),
    ])
    ev = Evaluator(test_session)
    rows = {r["template_name"]: r for r in ev.template_effectiveness()}
    assert abs(rows["A"]["interview_rate"] - 0.5) < 1e-9
    assert abs(rows["B"]["interview_rate"] - 1.0) < 1e-9


def test_ats_correlation_runs(test_session):
    _seed(test_session, [
        ("interview", 80, "A", "fintech"),
        ("no_response", 30, "A", "fintech"),
        ("offer", 95, "B", "ai"),
        ("rejected", 20, "B", "ai"),
    ])
    ev = Evaluator(test_session)
    out = ev.ats_outcome_correlation()
    assert -1.0 <= out["correlation"] <= 1.0
    assert "buckets" in out


def test_industry_effectiveness(test_session):
    _seed(test_session, [
        ("interview", 80, "A", "fintech"),
        ("no_response", 40, "A", "fintech"),
        ("offer", 90, "B", "ai"),
    ])
    ev = Evaluator(test_session)
    by_ind = {r["industry"]: r for r in ev.industry_effectiveness()}
    assert abs(by_ind["fintech"]["interview_rate"] - 0.5) < 1e-9
    assert by_ind["ai"]["sample_size"] == 1


def test_empty_is_safe(test_session):
    ev = Evaluator(test_session)
    assert ev.interview_rate() == {"interview_rate": 0.0, "total": 0, "interviews": 0}
    assert ev.ats_outcome_correlation()["correlation"] == 0.0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest backend/tests/unit/test_optimization_evaluator.py -v --no-cov`
Expected: FAIL — `ModuleNotFoundError: backend.services.optimization.evaluator`.

- [ ] **Step 3: Create the package marker**

```python
# backend/services/optimization/__init__.py
```
(empty file)

- [ ] **Step 4: Write the evaluator**

```python
# backend/services/optimization/evaluator.py
from __future__ import annotations

from collections import defaultdict

from sqlalchemy.orm import Session

from backend.repositories.outcome import OutcomeSignalRepository
from backend.services.learning.ranker import OutcomeRanker

STRONG_SIGNALS = {"phone_screen", "interview", "final_round", "offer", "accepted"}
WEAK_SIGNALS = {"applied", "no_response", "rejected"}


def _rate(signals: list) -> float:
    if not signals:
        return 0.0
    strong = sum(1 for s in signals if s.signal_type in STRONG_SIGNALS)
    return round(strong / len(signals), 4)


def _pearson(xs: list[float], ys: list[float]) -> float:
    n = len(xs)
    if n < 2:
        return 0.0
    mx = sum(xs) / n
    my = sum(ys) / n
    cov = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    vx = sum((x - mx) ** 2 for x in xs)
    vy = sum((y - my) ** 2 for y in ys)
    if vx == 0 or vy == 0:
        return 0.0
    return round(cov / (vx ** 0.5 * vy ** 0.5), 4)


class Evaluator:
    def __init__(self, session: Session) -> None:
        self._session = session
        self._repo = OutcomeSignalRepository(session)
        self._ranker = OutcomeRanker(session)

    def interview_rate(self) -> dict:
        signals = self._repo.list()
        interviews = sum(1 for s in signals if s.signal_type in STRONG_SIGNALS)
        total = len(signals)
        return {
            "interview_rate": round(interviews / total, 4) if total else 0.0,
            "total": total,
            "interviews": interviews,
        }

    def template_effectiveness(self) -> list[dict]:
        signals = self._repo.list()
        by_template: dict[str, list] = defaultdict(list)
        for s in signals:
            by_template[s.template_used or "unknown"].append(s)
        base = {r["template_name"]: r for r in self._ranker.get_template_rankings()}
        out = []
        for template, rows in by_template.items():
            row = dict(base.get(template, {"template_name": template}))
            row["interview_rate"] = _rate(rows)
            row["sample_size"] = len(rows)
            out.append(row)
        out.sort(key=lambda r: r["interview_rate"], reverse=True)
        return out

    def ats_outcome_correlation(self) -> dict:
        base = self._ranker.get_ats_vs_outcome_correlation()
        signals = [s for s in self._repo.list() if s.ats_score is not None]
        xs = [float(s.ats_score) for s in signals]
        ys = [1.0 if s.signal_type in STRONG_SIGNALS else 0.0 for s in signals]
        base["correlation"] = _pearson(xs, ys)
        return base

    def industry_effectiveness(self) -> list[dict]:
        signals = self._repo.list()
        by_ind: dict[str, list] = defaultdict(list)
        for s in signals:
            if s.industry:
                by_ind[s.industry].append(s)
        out = [
            {"industry": ind, "interview_rate": _rate(rows), "sample_size": len(rows)}
            for ind, rows in by_ind.items()
        ]
        out.sort(key=lambda r: r["interview_rate"], reverse=True)
        return out
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest backend/tests/unit/test_optimization_evaluator.py -v --no-cov`
Expected: 6 passed.

- [ ] **Step 6: Commit**

```bash
git add backend/services/optimization/__init__.py backend/services/optimization/evaluator.py backend/tests/unit/test_optimization_evaluator.py
git commit -m "feat(optimization): add Evaluator computing interview-rate, template/industry effectiveness, ATS correlation"
```

---

### Task 6: Guardrail validator

**Files:**
- Create: `backend/services/optimization/guardrails.py`
- Test: `backend/tests/unit/test_optimization_guardrails.py`

**Interfaces:**
- Produces: `validate_proposal(proposal: dict) -> None` (raises `GuardrailViolation` on failure) and `class GuardrailViolation(Exception)`.
- The validator enforces the Global Constraints at proposal-creation time. It rejects a proposal when ANY of:
  1. Missing/empty any of: `rationale`, `expected_impact`, `confidence_level`, `risk_level`, `target_engine`, `target_parameter`, `proposed_value`.
  2. `confidence_level` not in `{verified, strong_inference, weak_inference}`.
  3. `risk_level` not in `{low, medium, high}`.
  4. `target_engine` not in `{resume, ats, rag, cover_letter, copilot}`.
  5. **ATS-only optimization:** the proposal targets the ATS engine AND its `rationale`/`expected_impact` mention raising ATS score WITHOUT mentioning interview/conversion. Concretely: if `target_engine == "ats"` and the combined lowercased text of `rationale + expected_impact` contains `"ats score"` or `"ats_score"` but contains none of `{"interview", "conversion", "callback", "recruiter"}`, raise. (Primary objective is interview rate, not ATS score.)
  6. **High-risk + weak confidence:** `risk_level == "high"` and `confidence_level == "weak_inference"` → raise (too speculative to ever auto-surface for approval).

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/unit/test_optimization_guardrails.py
import pytest
from backend.services.optimization.guardrails import validate_proposal, GuardrailViolation


def _valid(**overrides):
    base = dict(
        target_engine="ats", target_parameter="ats_keyword_weight",
        proposed_value="0.40",
        rationale="Higher keyword weight correlates with more interviews in fintech.",
        expected_impact="+8% interview rate for fintech roles",
        confidence_level="strong_inference", risk_level="low",
    )
    base.update(overrides)
    return base


def test_valid_proposal_passes():
    validate_proposal(_valid())  # no raise


def test_missing_rationale_rejected():
    with pytest.raises(GuardrailViolation):
        validate_proposal(_valid(rationale=""))


def test_bad_confidence_rejected():
    with pytest.raises(GuardrailViolation):
        validate_proposal(_valid(confidence_level="guess"))


def test_bad_engine_rejected():
    with pytest.raises(GuardrailViolation):
        validate_proposal(_valid(target_engine="database"))


def test_ats_score_only_optimization_rejected():
    with pytest.raises(GuardrailViolation):
        validate_proposal(_valid(
            rationale="This raises the ATS score.",
            expected_impact="ATS score improves by 15 points",
        ))


def test_ats_change_justified_by_interviews_passes():
    validate_proposal(_valid(
        rationale="Raises ATS score AND historically lifts interview callbacks.",
        expected_impact="ATS score up; interview rate +6%",
    ))  # no raise — mentions interview


def test_high_risk_weak_confidence_rejected():
    with pytest.raises(GuardrailViolation):
        validate_proposal(_valid(risk_level="high", confidence_level="weak_inference"))
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest backend/tests/unit/test_optimization_guardrails.py -v --no-cov`
Expected: FAIL — `ModuleNotFoundError`.

- [ ] **Step 3: Write the guardrails**

```python
# backend/services/optimization/guardrails.py
from __future__ import annotations

_ENGINES = {"resume", "ats", "rag", "cover_letter", "copilot"}
_CONFIDENCE = {"verified", "strong_inference", "weak_inference"}
_RISK = {"low", "medium", "high"}
_REQUIRED = (
    "target_engine", "target_parameter", "proposed_value",
    "rationale", "expected_impact", "confidence_level", "risk_level",
)
_INTERVIEW_TERMS = ("interview", "conversion", "callback", "recruiter")


class GuardrailViolation(Exception):
    pass


def validate_proposal(proposal: dict) -> None:
    for field in _REQUIRED:
        value = proposal.get(field)
        if value is None or (isinstance(value, str) and not value.strip()):
            raise GuardrailViolation(f"Missing required field: {field}")

    if proposal["confidence_level"] not in _CONFIDENCE:
        raise GuardrailViolation(f"Invalid confidence_level: {proposal['confidence_level']}")
    if proposal["risk_level"] not in _RISK:
        raise GuardrailViolation(f"Invalid risk_level: {proposal['risk_level']}")
    if proposal["target_engine"] not in _ENGINES:
        raise GuardrailViolation(f"Invalid target_engine: {proposal['target_engine']}")

    if proposal["target_engine"] == "ats":
        text = f"{proposal['rationale']} {proposal['expected_impact']}".lower()
        mentions_ats = "ats score" in text or "ats_score" in text
        mentions_interview = any(term in text for term in _INTERVIEW_TERMS)
        if mentions_ats and not mentions_interview:
            raise GuardrailViolation(
                "ATS proposal justified by ATS score alone; primary objective is interview rate."
            )

    if proposal["risk_level"] == "high" and proposal["confidence_level"] == "weak_inference":
        raise GuardrailViolation("High-risk proposals require stronger than weak_inference confidence.")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest backend/tests/unit/test_optimization_guardrails.py -v --no-cov`
Expected: 7 passed.

- [ ] **Step 5: Commit**

```bash
git add backend/services/optimization/guardrails.py backend/tests/unit/test_optimization_guardrails.py
git commit -m "feat(optimization): add guardrail validator enforcing explainability and interview-rate primacy"
```

---
### Task 7: Recommender service (generates explainable proposals)

**Files:**
- Create: `backend/services/optimization/recommender.py`
- Test: `backend/tests/unit/test_optimization_recommender.py`

**Interfaces:**
- Consumes: `Evaluator` (Task 5), `validate_proposal`/`GuardrailViolation` (Task 6), `OptimizationProposalRepository` (Task 1), `SystemConfigRepository` (for current ATS weight values).
- Produces: `Recommender(session)` with `generate_proposals(min_sample_size: int = 5) -> list[OptimizationProposal]`.
  - Reads evaluation metrics, derives candidate changes, validates each through `validate_proposal`, persists each surviving candidate as a `pending` `OptimizationProposal`, and returns the created rows. Candidates failing guardrails are silently skipped (not persisted).
  - **Heuristics (deterministic, explainable — no LLM required):**
    1. **Template recommendation:** if `template_effectiveness()` has ≥2 templates each with `sample_size >= min_sample_size`, and the best template's `interview_rate` exceeds the worst by ≥0.15, propose switching the default resume template. `target_engine="resume"`, `target_parameter="default_template"`, `proposed_value=<best template>`, confidence `strong_inference` if both samples ≥10 else `weak_inference`, risk `low`. Rationale/impact mention the percentage gap and interview rate.
    2. **ATS weight recalibration:** if `ats_outcome_correlation()["correlation"] < 0.1` and total signals ≥ `min_sample_size`, propose lowering `ats_keyword_weight` by 0.05 (floor 0.1). `target_engine="ats"`. Rationale MUST mention interview rate (so it passes the guardrail). confidence `weak_inference`, risk `medium`.
    3. **Industry weighting:** for any industry with `sample_size >= min_sample_size` and `interview_rate >= 0.5`, propose an industry-specific note. `target_engine="resume"`, `target_parameter=f"industry_emphasis::{industry}"`, `proposed_value="increase"`, confidence `strong_inference`, risk `low`.
  - Each proposal stores an `evidence_json` with the metrics that justified it.
  - The Recommender NEVER applies a change — it only creates `pending` rows.

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/unit/test_optimization_recommender.py
from backend.services.optimization.recommender import Recommender
from backend.repositories.optimization import OptimizationProposalRepository
from backend.repositories.outcome import OutcomeSignalRepository
from backend.services.learning.ranker import _SIGNAL_WEIGHTS
from backend.models.application import Application


def _seed(session, rows):
    repo = OutcomeSignalRepository(session)
    app = Application(company="C", position="P"); session.add(app); session.flush()
    for st, ats, tpl, ind in rows:
        repo.create(application_id=app.id, signal_type=st,
                    signal_weight=_SIGNAL_WEIGHTS[st], ats_score=ats,
                    template_used=tpl, industry=ind)
    session.commit()


def test_template_proposal_created(test_session):
    # Template B clearly outperforms A on interview rate, both have >=5 samples.
    rows = []
    rows += [("no_response", 40, "A", "fintech")] * 5     # A: 0% interview
    rows += [("interview", 80, "B", "ai")] * 5            # B: 100% interview
    _seed(test_session, rows)

    rec = Recommender(test_session)
    created = rec.generate_proposals(min_sample_size=5)
    test_session.commit()

    repo = OptimizationProposalRepository(test_session)
    pending = repo.list_by_status("pending")
    assert any(p.target_parameter == "default_template" and p.proposed_value == "B"
               for p in pending)
    # All created proposals are pending and explainable.
    for p in created:
        assert p.status == "pending"
        assert p.rationale and p.expected_impact
        assert p.confidence_level in {"verified", "strong_inference", "weak_inference"}


def test_no_proposals_when_insufficient_data(test_session):
    _seed(test_session, [("interview", 80, "A", "ai")])  # only 1 signal
    rec = Recommender(test_session)
    created = rec.generate_proposals(min_sample_size=5)
    assert created == []


def test_ats_proposal_passes_guardrail(test_session):
    # Low ATS-outcome correlation + enough samples → ATS recalibration proposal.
    rows = [("interview", 10, "A", "ai")] * 3 + [("no_response", 95, "A", "ai")] * 3
    _seed(test_session, rows)
    rec = Recommender(test_session)
    created = rec.generate_proposals(min_sample_size=5)
    ats = [p for p in created if p.target_engine == "ats"]
    # If created, the rationale mentions interview (guardrail-compliant).
    for p in ats:
        assert "interview" in (p.rationale + p.expected_impact).lower()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest backend/tests/unit/test_optimization_recommender.py -v --no-cov`
Expected: FAIL — `ModuleNotFoundError`.

- [ ] **Step 3: Write the recommender**

```python
# backend/services/optimization/recommender.py
from __future__ import annotations

import json

from sqlalchemy.orm import Session

from backend.repositories.optimization import OptimizationProposalRepository
from backend.repositories.system_config import SystemConfigRepository
from backend.services.optimization.evaluator import Evaluator
from backend.services.optimization.guardrails import validate_proposal, GuardrailViolation


class Recommender:
    def __init__(self, session: Session) -> None:
        self._session = session
        self._eval = Evaluator(session)
        self._proposals = OptimizationProposalRepository(session)
        self._config = SystemConfigRepository(session)

    def _persist(self, candidate: dict):
        try:
            validate_proposal(candidate)
        except GuardrailViolation:
            return None
        return self._proposals.create(**candidate)

    def generate_proposals(self, min_sample_size: int = 5) -> list:
        created = []

        # Heuristic 1: template switch
        templates = [t for t in self._eval.template_effectiveness()
                     if t.get("sample_size", 0) >= min_sample_size]
        if len(templates) >= 2:
            best, worst = templates[0], templates[-1]
            gap = best["interview_rate"] - worst["interview_rate"]
            if gap >= 0.15:
                both_large = best["sample_size"] >= 10 and worst["sample_size"] >= 10
                pct = round(gap * 100)
                c = self._persist({
                    "target_engine": "resume",
                    "target_parameter": "default_template",
                    "current_value": worst["template_name"],
                    "proposed_value": best["template_name"],
                    "rationale": (
                        f"Template '{best['template_name']}' shows a "
                        f"{best['interview_rate']:.0%} interview rate vs "
                        f"'{worst['template_name']}' at {worst['interview_rate']:.0%}."
                    ),
                    "expected_impact": f"~{pct}% higher interview rate by switching default template.",
                    "confidence_level": "strong_inference" if both_large else "weak_inference",
                    "risk_level": "low",
                    "evidence_json": json.dumps({"templates": templates}),
                })
                if c:
                    created.append(c)

        # Heuristic 2: ATS recalibration (justified by interview rate)
        corr = self._eval.ats_outcome_correlation()
        total = corr.get("total_signals", 0)
        if total >= min_sample_size and corr["correlation"] < 0.1:
            current = self._config.get_value("ats_keyword_weight", "0.35") or "0.35"
            new_val = max(0.1, round(float(current) - 0.05, 2))
            c = self._persist({
                "target_engine": "ats",
                "target_parameter": "ats_keyword_weight",
                "current_value": current,
                "proposed_value": str(new_val),
                "rationale": (
                    "ATS score shows near-zero correlation with interview outcomes "
                    f"(r={corr['correlation']}); reducing keyword weight should improve "
                    "readability without hurting the interview rate."
                ),
                "expected_impact": "Neutral-to-positive interview rate; better human readability.",
                "confidence_level": "weak_inference",
                "risk_level": "medium",
                "evidence_json": json.dumps(corr),
            })
            if c:
                created.append(c)

        # Heuristic 3: industry emphasis
        for ind in self._eval.industry_effectiveness():
            if ind["sample_size"] >= min_sample_size and ind["interview_rate"] >= 0.5:
                c = self._persist({
                    "target_engine": "resume",
                    "target_parameter": f"industry_emphasis::{ind['industry']}",
                    "current_value": None,
                    "proposed_value": "increase",
                    "rationale": (
                        f"{ind['industry']} roles convert at "
                        f"{ind['interview_rate']:.0%} interview rate "
                        f"(n={ind['sample_size']}); emphasize matching experience."
                    ),
                    "expected_impact": f"Higher interview rate for {ind['industry']} applications.",
                    "confidence_level": "strong_inference",
                    "risk_level": "low",
                    "evidence_json": json.dumps(ind),
                })
                if c:
                    created.append(c)

        return created
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest backend/tests/unit/test_optimization_recommender.py -v --no-cov`
Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add backend/services/optimization/recommender.py backend/tests/unit/test_optimization_recommender.py
git commit -m "feat(optimization): add Recommender generating guardrail-validated pending proposals"
```

---

### Task 8: Applier service (human-gated apply + reversible revert)

**Files:**
- Create: `backend/services/optimization/applier.py`
- Test: `backend/tests/unit/test_optimization_applier.py`

**Interfaces:**
- Consumes: `OptimizationProposalRepository`, `OptimizationLogRepository`, `PromptVersionRepository` (Tasks 1–3), `SystemConfigRepository`.
- Produces: `Applier(session)` with:
  - `approve(proposal_id: str) -> OptimizationProposal` — sets `status="approved"`, `decided_at=utcnow()`. Does NOT apply yet. Raises `ValueError` if proposal missing or not `pending`.
  - `reject(proposal_id: str) -> OptimizationProposal` — sets `status="rejected"`, `decided_at`. Raises if not `pending`.
  - `apply(proposal_id: str) -> OptimizationLog` — **refuses unless `status == "approved"`** (raises `ApprovalRequired`). Applies the change to the target:
    - ATS / config-style parameters (engine `ats`, or any `target_parameter` that exists as a `system_config` key) → `SystemConfigRepository.set_value(param, proposed_value)`; records `old_value` from the prior config value.
    - For non-config parameters (e.g. `default_template`, `industry_emphasis::*`) → also stored via `SystemConfigRepository.set_value` (these become new config keys). The point is every applied change lands in a single reversible store.
    - Writes an `OptimizationLog(action="applied", old_value=<prior>, new_value=<proposed>)`. Returns the log row. (Status stays `approved`; the log is the record of application.)
  - `revert(proposal_id: str) -> OptimizationLog` — finds the most recent `applied` log for the proposal, restores `old_value` via `SystemConfigRepository.set_value`, writes a new `OptimizationLog(action="reverted", old_value=<current>, new_value=<restored>)`, and sets proposal `status="reverted"`. Raises `ValueError` if no applied log exists.
- Define `class ApprovalRequired(Exception)`.

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/unit/test_optimization_applier.py
import pytest
from backend.services.optimization.applier import Applier, ApprovalRequired
from backend.repositories.optimization import (
    OptimizationProposalRepository, OptimizationLogRepository,
)
from backend.repositories.system_config import SystemConfigRepository


def _make(session, **overrides):
    repo = OptimizationProposalRepository(session)
    base = dict(
        target_engine="ats", target_parameter="ats_keyword_weight",
        current_value="0.35", proposed_value="0.30",
        rationale="r mentions interview", expected_impact="interview rate up",
        confidence_level="strong_inference", risk_level="low",
    )
    base.update(overrides)
    p = repo.create(**base); session.commit()
    return p


def test_apply_requires_approval(test_session):
    p = _make(test_session)
    applier = Applier(test_session)
    with pytest.raises(ApprovalRequired):
        applier.apply(p.id)            # still pending → refused


def test_full_approve_apply_revert_cycle(test_session):
    cfg = SystemConfigRepository(test_session)
    cfg.set_value("ats_keyword_weight", "0.35"); test_session.commit()
    p = _make(test_session)
    applier = Applier(test_session)

    applier.approve(p.id); test_session.commit()
    assert OptimizationProposalRepository(test_session).get(p.id).status == "approved"

    log = applier.apply(p.id); test_session.commit()
    assert log.action == "applied"
    assert log.old_value == "0.35" and log.new_value == "0.30"
    assert cfg.get_value("ats_keyword_weight") == "0.30"

    rev = applier.revert(p.id); test_session.commit()
    assert rev.action == "reverted"
    assert cfg.get_value("ats_keyword_weight") == "0.35"   # restored
    assert OptimizationProposalRepository(test_session).get(p.id).status == "reverted"
    # Audit trail has both entries.
    logs = OptimizationLogRepository(test_session).list_for_proposal(p.id)
    assert {l.action for l in logs} == {"applied", "reverted"}


def test_reject_blocks_apply(test_session):
    p = _make(test_session)
    applier = Applier(test_session)
    applier.reject(p.id); test_session.commit()
    with pytest.raises(ApprovalRequired):
        applier.apply(p.id)


def test_revert_without_apply_raises(test_session):
    p = _make(test_session)
    applier = Applier(test_session)
    applier.approve(p.id); test_session.commit()
    with pytest.raises(ValueError):
        applier.revert(p.id)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest backend/tests/unit/test_optimization_applier.py -v --no-cov`
Expected: FAIL — `ModuleNotFoundError`.

- [ ] **Step 3: Write the applier**

```python
# backend/services/optimization/applier.py
from __future__ import annotations

from sqlalchemy.orm import Session

from backend.models.base import utcnow
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

    def _get_pending(self, proposal_id: str):
        p = self._proposals.get(proposal_id)
        if p is None:
            raise ValueError(f"Proposal {proposal_id} not found")
        if p.status != "pending":
            raise ValueError(f"Proposal {proposal_id} is not pending (status={p.status})")
        return p

    def approve(self, proposal_id: str):
        p = self._get_pending(proposal_id)
        p.status = "approved"
        p.decided_at = utcnow()
        self._session.flush()
        return p

    def reject(self, proposal_id: str):
        p = self._get_pending(proposal_id)
        p.status = "rejected"
        p.decided_at = utcnow()
        self._session.flush()
        return p

    def apply(self, proposal_id: str):
        p = self._proposals.get(proposal_id)
        if p is None:
            raise ValueError(f"Proposal {proposal_id} not found")
        if p.status != "approved":
            raise ApprovalRequired(
                f"Proposal {proposal_id} must be approved before apply (status={p.status})"
            )
        old_value = self._config.get_value(p.target_parameter)
        self._config.set_value(p.target_parameter, p.proposed_value)
        log = self._logs.create(
            proposal_id=p.id, action="applied",
            target_engine=p.target_engine, target_parameter=p.target_parameter,
            old_value=old_value, new_value=p.proposed_value,
        )
        self._session.flush()
        return log

    def revert(self, proposal_id: str):
        applied = [l for l in self._logs.list_for_proposal(proposal_id) if l.action == "applied"]
        if not applied:
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest backend/tests/unit/test_optimization_applier.py -v --no-cov`
Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add backend/services/optimization/applier.py backend/tests/unit/test_optimization_applier.py
git commit -m "feat(optimization): add Applier enforcing approval gate with reversible apply/revert + audit log"
```

---
### Task 9: Prompt evolution service (seed, variant, version, activate)

**Files:**
- Create: `backend/services/optimization/prompt_evolver.py`
- Test: `backend/tests/unit/test_prompt_evolver.py`

**Interfaces:**
- Consumes: `PromptVersionRepository` (Task 3), `PromptLoader` (`backend/services/prompt_loader.py`).
- Produces: `PromptEvolver(session)` with:
  - `seed_from_disk(prompt_name: str) -> PromptVersion` — reads the on-disk YAML via `PromptLoader().load(prompt_name)`, creates a `PromptVersion` (version from the file's `version` field, default `"1.0"`) marked `is_active=True` if no active version exists yet. Idempotent: if a version with that `(prompt_name, version)` already exists, returns it unchanged.
  - `create_variant(prompt_name: str, content_yaml: str, change_rationale: str) -> PromptVersion` — creates a new INACTIVE version. Auto-increments the minor version from the current highest version of that prompt (e.g. `1.0` → `1.1`; `1.9` → `1.10`). Sets `parent_version` to the prior highest. Does NOT activate (human-gated).
  - `activate(version_id: str) -> PromptVersion` — delegates to `PromptVersionRepository.activate` (single-active invariant; reversible).
  - `get_active_content(prompt_name: str) -> str | None` — returns the active version's `content_yaml`, or `None` if none is active.
- **Reversibility:** activating a different version never deletes the prior one (enforced by Task 3's repo). Reverting a prompt = `activate(prior_version_id)`.

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/unit/test_prompt_evolver.py
from backend.services.optimization.prompt_evolver import PromptEvolver
from backend.repositories.optimization import PromptVersionRepository


def test_seed_from_disk_creates_active_version(test_session):
    ev = PromptEvolver(test_session)
    v = ev.seed_from_disk("resume/generate")   # real on-disk prompt
    test_session.commit()
    assert v.is_active is True
    assert v.content_yaml                       # non-empty
    # idempotent
    again = ev.seed_from_disk("resume/generate")
    assert again.id == v.id


def test_create_variant_increments_minor(test_session):
    ev = PromptEvolver(test_session)
    base = ev.seed_from_disk("ats/score_ats"); test_session.commit()
    variant = ev.create_variant(
        "ats/score_ats", content_yaml="system: tuned", change_rationale="tighter scoring"
    )
    test_session.commit()
    assert variant.is_active is False
    assert variant.parent_version == base.version
    # version string advanced
    assert variant.version != base.version


def test_activate_and_revert(test_session):
    ev = PromptEvolver(test_session)
    base = ev.seed_from_disk("resume/generate"); test_session.commit()
    variant = ev.create_variant("resume/generate", "system: v2", "experiment")
    test_session.commit()
    ev.activate(variant.id); test_session.commit()
    assert ev.get_active_content("resume/generate") == "system: v2"
    # revert by re-activating base
    ev.activate(base.id); test_session.commit()
    assert ev.get_active_content("resume/generate") == base.content_yaml
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest backend/tests/unit/test_prompt_evolver.py -v --no-cov`
Expected: FAIL — `ModuleNotFoundError`.

- [ ] **Step 3: Write the evolver**

```python
# backend/services/optimization/prompt_evolver.py
from __future__ import annotations

import yaml
from sqlalchemy.orm import Session

from backend.repositories.optimization import PromptVersionRepository
from backend.services.prompt_loader import PromptLoader


def _next_minor(version: str) -> str:
    """'1.0' -> '1.1', '1.9' -> '1.10', '2' -> '2.1'."""
    parts = version.split(".")
    if len(parts) == 1:
        return f"{parts[0]}.1"
    major, minor = parts[0], parts[1]
    return f"{major}.{int(minor) + 1}"


def _highest(versions: list) -> str | None:
    if not versions:
        return None
    def key(v):
        parts = v.version.split(".")
        return tuple(int(p) if p.isdigit() else 0 for p in parts)
    return max(versions, key=key).version


class PromptEvolver:
    def __init__(self, session: Session) -> None:
        self._session = session
        self._repo = PromptVersionRepository(session)
        self._loader = PromptLoader()

    def seed_from_disk(self, prompt_name: str):
        data = self._loader.load(prompt_name)
        version = str(data.get("version", "1.0"))
        existing = [v for v in self._repo.list_for_prompt(prompt_name) if v.version == version]
        if existing:
            return existing[0]
        content = yaml.safe_dump(
            {"version": version, "system": data["system"], "user_template": data["user_template"]},
            sort_keys=False,
        )
        has_active = self._repo.get_active(prompt_name) is not None
        v = self._repo.create(
            prompt_name=prompt_name, version=version,
            content_yaml=content, is_active=not has_active,
        )
        return v

    def create_variant(self, prompt_name: str, content_yaml: str, change_rationale: str):
        versions = self._repo.list_for_prompt(prompt_name)
        prior = _highest(versions)
        new_version = _next_minor(prior) if prior else "1.1"
        return self._repo.create(
            prompt_name=prompt_name, version=new_version,
            content_yaml=content_yaml, is_active=False,
            parent_version=prior, change_rationale=change_rationale,
        )

    def activate(self, version_id: str):
        return self._repo.activate(version_id)

    def get_active_content(self, prompt_name: str) -> str | None:
        active = self._repo.get_active(prompt_name)
        return active.content_yaml if active else None
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest backend/tests/unit/test_prompt_evolver.py -v --no-cov`
Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add backend/services/optimization/prompt_evolver.py backend/tests/unit/test_prompt_evolver.py
git commit -m "feat(optimization): add PromptEvolver for versioned, reversible prompt variants"
```

---

### Task 10: A/B testing service (record + conclude on interview conversion)

**Files:**
- Create: `backend/services/optimization/ab_testing.py`
- Test: `backend/tests/unit/test_ab_testing.py`

**Interfaces:**
- Consumes: `ABExperimentRepository`, `ABVariantRepository` (Task 4).
- Produces: `ABTestingService(session)` with:
  - `create_experiment(name: str, target_engine: str, variant_a: dict, variant_b: dict) -> ABExperiment` — creates a `running` experiment plus two variants (`label="A"`, `label="B"`) with `config_json=json.dumps(variant_x)`.
  - `record_impression(variant_id: str) -> None` — increments `impressions`.
  - `record_conversion(variant_id: str) -> None` — increments `conversions` (a conversion = the application using this variant reached a strong signal).
  - `conversion_rate(variant_id: str) -> float` — `conversions / impressions` (0.0 if no impressions).
  - `conclude(experiment_id: str) -> ABExperiment` — sets `status="concluded"`, `concluded_at`, and `winner_variant_id` = the variant with the higher conversion rate (ties → variant A). Requires each variant to have `impressions >= 1`; raises `ValueError` otherwise (cannot conclude on no data).
- The decision metric is interview conversion rate — never ATS score.

- [ ] **Step 1: Write the failing test**

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest backend/tests/unit/test_ab_testing.py -v --no-cov`
Expected: FAIL — `ModuleNotFoundError`.

- [ ] **Step 3: Write the service**

```python
# backend/services/optimization/ab_testing.py
from __future__ import annotations

import json

from sqlalchemy.orm import Session

from backend.models.base import utcnow
from backend.repositories.optimization import ABExperimentRepository, ABVariantRepository


class ABTestingService:
    def __init__(self, session: Session) -> None:
        self._session = session
        self._exp = ABExperimentRepository(session)
        self._var = ABVariantRepository(session)

    def create_experiment(self, name: str, target_engine: str,
                          variant_a: dict, variant_b: dict):
        exp = self._exp.create(name=name, target_engine=target_engine)
        self._var.create(experiment_id=exp.id, label="A", config_json=json.dumps(variant_a))
        self._var.create(experiment_id=exp.id, label="B", config_json=json.dumps(variant_b))
        self._session.flush()
        return exp

    def record_impression(self, variant_id: str) -> None:
        v = self._var.get(variant_id)
        if v is None:
            raise ValueError(f"Variant {variant_id} not found")
        v.impressions += 1
        self._session.flush()

    def record_conversion(self, variant_id: str) -> None:
        v = self._var.get(variant_id)
        if v is None:
            raise ValueError(f"Variant {variant_id} not found")
        v.conversions += 1
        self._session.flush()

    def conversion_rate(self, variant_id: str) -> float:
        v = self._var.get(variant_id)
        if v is None or v.impressions == 0:
            return 0.0
        return round(v.conversions / v.impressions, 4)

    def conclude(self, experiment_id: str):
        exp = self._exp.get(experiment_id)
        if exp is None:
            raise ValueError(f"Experiment {experiment_id} not found")
        variants = self._var.list_for_experiment(experiment_id)
        if len(variants) < 2 or any(v.impressions < 1 for v in variants):
            raise ValueError("Cannot conclude: every variant needs at least one impression.")
        # Highest conversion rate wins; ties resolved toward label 'A'.
        ranked = sorted(
            variants,
            key=lambda v: (v.conversions / v.impressions, v.label == "A"),
            reverse=True,
        )
        exp.winner_variant_id = ranked[0].id
        exp.status = "concluded"
        exp.concluded_at = utcnow()
        self._session.flush()
        return exp
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest backend/tests/unit/test_ab_testing.py -v --no-cov`
Expected: 2 passed.

- [ ] **Step 5: Commit**

```bash
git add backend/services/optimization/ab_testing.py backend/tests/unit/test_ab_testing.py
git commit -m "feat(optimization): add A/B testing service scored on interview conversion rate"
```

---
### Task 11: Learning-loop orchestrator (fires every N applications)

**Files:**
- Create: `backend/services/optimization/loop.py`
- Test: `backend/tests/unit/test_optimization_loop.py`

**Interfaces:**
- Consumes: `Recommender` (Task 7), `Evaluator` (Task 5), `SystemConfigRepository` (for `learning_trigger_count`), `OutcomeSignalRepository` (for the application count).
- Produces: `LearningLoop(session)` with:
  - `should_run() -> bool` — returns `True` when the count of outcome signals is a positive multiple of `learning_trigger_count` (read from config, default 5). Uses the count of distinct `application_id` values among outcome signals as the "applications" measure.
  - `run() -> dict` — executes one optimization cycle and returns a summary:
    1. Compute `Evaluator` metrics snapshot (interview_rate, template_effectiveness, ats_outcome_correlation, industry_effectiveness).
    2. Call `Recommender.generate_proposals()`.
    3. Return `{"ran": True, "metrics": {...}, "proposals_created": <int>, "proposal_ids": [...]}`.
  - `maybe_run() -> dict` — calls `run()` if `should_run()` else returns `{"ran": False, "reason": "trigger threshold not reached"}`.
- The loop NEVER applies changes — it only refreshes metrics and creates `pending` proposals. (Embedding/index refresh is delegated to the existing `/learning/reindex` endpoint, invoked separately by the route in Task 12; the loop itself stays pure and testable without Ollama.)

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/unit/test_optimization_loop.py
from backend.services.optimization.loop import LearningLoop
from backend.repositories.outcome import OutcomeSignalRepository
from backend.repositories.system_config import SystemConfigRepository
from backend.services.learning.ranker import _SIGNAL_WEIGHTS
from backend.models.application import Application


def _seed_apps(session, n, signal="interview", template="A", industry="ai"):
    repo = OutcomeSignalRepository(session)
    for _ in range(n):
        app = Application(company="C", position="P"); session.add(app); session.flush()
        repo.create(application_id=app.id, signal_type=signal,
                    signal_weight=_SIGNAL_WEIGHTS[signal], ats_score=70,
                    template_used=template, industry=industry)
    session.commit()


def test_should_run_on_multiple_of_trigger(test_session):
    cfg = SystemConfigRepository(test_session)
    cfg.set_value("learning_trigger_count", "5"); test_session.commit()
    loop = LearningLoop(test_session)
    _seed_apps(test_session, 4)
    assert loop.should_run() is False
    _seed_apps(test_session, 1)            # now 5
    assert loop.should_run() is True


def test_maybe_run_creates_proposals_when_triggered(test_session):
    cfg = SystemConfigRepository(test_session)
    cfg.set_value("learning_trigger_count", "5"); test_session.commit()
    # 5 of template A (100% interview) + 5 of template B (0%) → template proposal expected
    _seed_apps(test_session, 5, signal="interview", template="A")
    _seed_apps(test_session, 5, signal="no_response", template="B")
    loop = LearningLoop(test_session)
    out = loop.maybe_run(); test_session.commit()
    assert out["ran"] is True
    assert out["proposals_created"] >= 1
    assert "interview_rate" in out["metrics"]


def test_maybe_run_skips_when_not_triggered(test_session):
    cfg = SystemConfigRepository(test_session)
    cfg.set_value("learning_trigger_count", "5"); test_session.commit()
    _seed_apps(test_session, 3)
    loop = LearningLoop(test_session)
    out = loop.maybe_run()
    assert out["ran"] is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest backend/tests/unit/test_optimization_loop.py -v --no-cov`
Expected: FAIL — `ModuleNotFoundError`.

- [ ] **Step 3: Write the loop**

```python
# backend/services/optimization/loop.py
from __future__ import annotations

from sqlalchemy.orm import Session

from backend.repositories.outcome import OutcomeSignalRepository
from backend.repositories.system_config import SystemConfigRepository
from backend.services.optimization.evaluator import Evaluator
from backend.services.optimization.recommender import Recommender


class LearningLoop:
    def __init__(self, session: Session) -> None:
        self._session = session
        self._outcomes = OutcomeSignalRepository(session)
        self._config = SystemConfigRepository(session)
        self._eval = Evaluator(session)
        self._rec = Recommender(session)

    def _application_count(self) -> int:
        return len({s.application_id for s in self._outcomes.list()})

    def _trigger_count(self) -> int:
        raw = self._config.get_value("learning_trigger_count", "5") or "5"
        try:
            return max(1, int(raw))
        except ValueError:
            return 5

    def should_run(self) -> bool:
        count = self._application_count()
        trigger = self._trigger_count()
        return count > 0 and count % trigger == 0

    def run(self) -> dict:
        metrics = {
            "interview_rate": self._eval.interview_rate(),
            "template_effectiveness": self._eval.template_effectiveness(),
            "ats_outcome_correlation": self._eval.ats_outcome_correlation(),
            "industry_effectiveness": self._eval.industry_effectiveness(),
        }
        created = self._rec.generate_proposals(min_sample_size=self._trigger_count())
        return {
            "ran": True,
            "metrics": metrics,
            "proposals_created": len(created),
            "proposal_ids": [p.id for p in created],
        }

    def maybe_run(self) -> dict:
        if not self.should_run():
            return {"ran": False, "reason": "trigger threshold not reached"}
        return self.run()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest backend/tests/unit/test_optimization_loop.py -v --no-cov`
Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add backend/services/optimization/loop.py backend/tests/unit/test_optimization_loop.py
git commit -m "feat(optimization): add learning-loop orchestrator firing every N applications"
```

---

### Task 12: Optimization API routes (proposals + loop)

**Files:**
- Create: `backend/api/v1/routes/optimization.py`
- Modify: `backend/main.py` (register `optimization_router`)
- Test: `backend/tests/integration/test_optimization_routes.py`

**Interfaces:**
- Consumes: `Recommender`, `Applier` (+ `ApprovalRequired`), `LearningLoop`, `OptimizationProposalRepository`, `OptimizationLogRepository`, `get_session`.
- Produces an `APIRouter` (no internal prefix; mounted at `/api/v1`) with:
  - `GET /optimization/proposals?status=<optional>` → `{"proposals": [ ... ]}` (serialize all proposal columns). Filters by status when provided.
  - `POST /optimization/proposals/generate` → runs `Recommender.generate_proposals()`, returns `{"created": <int>, "proposal_ids": [...]}`.
  - `POST /optimization/proposals/{id}/approve` → `Applier.approve`; 404 if missing, 409 if not pending.
  - `POST /optimization/proposals/{id}/reject` → `Applier.reject`; same error mapping.
  - `POST /optimization/proposals/{id}/apply` → `Applier.apply`; returns the log; **409 `ApprovalRequired`** if not approved.
  - `POST /optimization/proposals/{id}/revert` → `Applier.revert`; 409 if nothing applied.
  - `GET /optimization/logs?limit=50` → `{"logs": [...]}` from `OptimizationLogRepository.list_recent`.
  - `POST /optimization/loop/run` → `LearningLoop.maybe_run()`, returns its dict.
- Serialization helper `_serialize_proposal(p)` returns a plain dict of all columns.

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/integration/test_optimization_routes.py
import pytest
from backend.database import seed_system_config
from backend.repositories.outcome import OutcomeSignalRepository
from backend.services.learning.ranker import _SIGNAL_WEIGHTS
from backend.models.application import Application


@pytest.fixture
def seeded(test_session):
    seed_system_config(test_session)
    repo = OutcomeSignalRepository(test_session)
    # 5 strong (template A) + 5 weak (template B) → template proposal
    for sig, tpl, n in (("interview", "A", 5), ("no_response", "B", 5)):
        for _ in range(n):
            app = Application(company="C", position="P"); test_session.add(app); test_session.flush()
            repo.create(application_id=app.id, signal_type=sig,
                        signal_weight=_SIGNAL_WEIGHTS[sig], ats_score=70,
                        template_used=tpl, industry="ai")
    test_session.commit()


def test_generate_list_approve_apply_revert(client, seeded):
    gen = client.post("/api/v1/optimization/proposals/generate")
    assert gen.status_code == 200, gen.text
    assert gen.json()["created"] >= 1

    listing = client.get("/api/v1/optimization/proposals?status=pending")
    assert listing.status_code == 200
    proposals = listing.json()["proposals"]
    pid = proposals[0]["id"]

    # apply before approve → 409
    early = client.post(f"/api/v1/optimization/proposals/{pid}/apply")
    assert early.status_code == 409

    assert client.post(f"/api/v1/optimization/proposals/{pid}/approve").status_code == 200
    applied = client.post(f"/api/v1/optimization/proposals/{pid}/apply")
    assert applied.status_code == 200
    assert applied.json()["action"] == "applied"

    reverted = client.post(f"/api/v1/optimization/proposals/{pid}/revert")
    assert reverted.status_code == 200
    assert reverted.json()["action"] == "reverted"

    logs = client.get("/api/v1/optimization/logs")
    assert logs.status_code == 200
    assert len(logs.json()["logs"]) >= 2


def test_reject_then_apply_blocked(client, seeded):
    client.post("/api/v1/optimization/proposals/generate")
    pid = client.get("/api/v1/optimization/proposals").json()["proposals"][0]["id"]
    assert client.post(f"/api/v1/optimization/proposals/{pid}/reject").status_code == 200
    assert client.post(f"/api/v1/optimization/proposals/{pid}/apply").status_code == 409


def test_loop_run_endpoint(client, seeded):
    out = client.post("/api/v1/optimization/loop/run")
    assert out.status_code == 200
    assert out.json()["ran"] is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest backend/tests/integration/test_optimization_routes.py -v --no-cov`
Expected: FAIL — 404s (router not registered).

- [ ] **Step 3: Write the router**

```python
# backend/api/v1/routes/optimization.py
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from backend.database import get_session
from backend.repositories.optimization import (
    OptimizationProposalRepository, OptimizationLogRepository,
)
from backend.services.optimization.applier import Applier, ApprovalRequired
from backend.services.optimization.recommender import Recommender
from backend.services.optimization.loop import LearningLoop

router = APIRouter(tags=["optimization"])


def _serialize_proposal(p) -> dict:
    return {
        "id": p.id, "target_engine": p.target_engine,
        "target_parameter": p.target_parameter, "current_value": p.current_value,
        "proposed_value": p.proposed_value, "rationale": p.rationale,
        "expected_impact": p.expected_impact, "confidence_level": p.confidence_level,
        "risk_level": p.risk_level, "evidence_json": p.evidence_json,
        "status": p.status, "created_at": p.created_at,
        "updated_at": p.updated_at, "decided_at": p.decided_at,
    }


def _serialize_log(l) -> dict:
    return {
        "id": l.id, "proposal_id": l.proposal_id, "action": l.action,
        "target_engine": l.target_engine, "target_parameter": l.target_parameter,
        "old_value": l.old_value, "new_value": l.new_value,
        "actor": l.actor, "created_at": l.created_at,
    }


@router.get("/optimization/proposals")
def list_proposals(
    status: str | None = Query(default=None), session: Session = Depends(get_session)
) -> dict:
    repo = OptimizationProposalRepository(session)
    rows = repo.list_by_status(status) if status else repo.list()
    return {"proposals": [_serialize_proposal(p) for p in rows]}


@router.post("/optimization/proposals/generate")
def generate_proposals(session: Session = Depends(get_session)) -> dict:
    created = Recommender(session).generate_proposals()
    return {"created": len(created), "proposal_ids": [p.id for p in created]}


@router.post("/optimization/proposals/{proposal_id}/approve")
def approve_proposal(proposal_id: str, session: Session = Depends(get_session)) -> dict:
    try:
        p = Applier(session).approve(proposal_id)
    except ValueError as exc:
        _raise_not_found_or_conflict(exc)
    return _serialize_proposal(p)


@router.post("/optimization/proposals/{proposal_id}/reject")
def reject_proposal(proposal_id: str, session: Session = Depends(get_session)) -> dict:
    try:
        p = Applier(session).reject(proposal_id)
    except ValueError as exc:
        _raise_not_found_or_conflict(exc)
    return _serialize_proposal(p)


@router.post("/optimization/proposals/{proposal_id}/apply")
def apply_proposal(proposal_id: str, session: Session = Depends(get_session)) -> dict:
    try:
        log = Applier(session).apply(proposal_id)
    except ApprovalRequired as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return _serialize_log(log)


@router.post("/optimization/proposals/{proposal_id}/revert")
def revert_proposal(proposal_id: str, session: Session = Depends(get_session)) -> dict:
    try:
        log = Applier(session).revert(proposal_id)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    return _serialize_log(log)


@router.get("/optimization/logs")
def list_logs(limit: int = 50, session: Session = Depends(get_session)) -> dict:
    logs = OptimizationLogRepository(session).list_recent(limit=limit)
    return {"logs": [_serialize_log(l) for l in logs]}


@router.post("/optimization/loop/run")
def run_loop(session: Session = Depends(get_session)) -> dict:
    return LearningLoop(session).maybe_run()


def _raise_not_found_or_conflict(exc: ValueError) -> None:
    msg = str(exc)
    if "not found" in msg:
        raise HTTPException(status_code=404, detail=msg)
    raise HTTPException(status_code=409, detail=msg)
```

- [ ] **Step 4: Register the router**

In `backend/main.py`, add the import beside the other route imports:
```python
from backend.api.v1.routes.optimization import router as optimization_router
```
And in `create_app()`, after the settings router registration:
```python
app.include_router(optimization_router, prefix="/api/v1")
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest backend/tests/integration/test_optimization_routes.py -v --no-cov`
Expected: 3 passed.

- [ ] **Step 6: Commit**

```bash
git add backend/api/v1/routes/optimization.py backend/main.py backend/tests/integration/test_optimization_routes.py
git commit -m "feat(optimization): add optimization API routes for proposals, logs, and learning loop"
```

---
### Task 13: A/B testing + prompt-version API routes

**Files:**
- Modify: `backend/api/v1/routes/optimization.py` (add A/B + prompt endpoints to the same router)
- Test: `backend/tests/integration/test_ab_prompt_routes.py`

**Interfaces:**
- Consumes: `ABTestingService` (Task 10), `ABExperimentRepository`, `ABVariantRepository`, `PromptEvolver` (Task 9), `PromptVersionRepository`.
- Adds to the existing optimization router:
  - `POST /optimization/experiments` body `{name, target_engine, variant_a: object, variant_b: object}` → creates experiment + variants, returns `{"experiment_id", "variant_ids": {"A":..., "B":...}}`.
  - `GET /optimization/experiments` → `{"experiments": [{id, name, target_engine, metric, status, winner_variant_id, variants: [{id, label, impressions, conversions, conversion_rate}]}]}`.
  - `POST /optimization/experiments/variants/{variant_id}/impression` → increments impression, returns `{"ok": true}`.
  - `POST /optimization/experiments/variants/{variant_id}/conversion` → increments conversion.
  - `POST /optimization/experiments/{experiment_id}/conclude` → concludes; 409 on insufficient data; returns serialized experiment.
  - `GET /optimization/prompts/{prompt_name:path}/versions` → `{"versions": [{id, version, is_active, parent_version, change_rationale, created_at}]}`. Uses `:path` converter because prompt names contain `/`.
  - `POST /optimization/prompts/{prompt_name:path}/seed` → `PromptEvolver.seed_from_disk`, returns the version row.
  - `POST /optimization/prompts/versions/{version_id}/activate` → `PromptEvolver.activate`, returns the activated row.

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/integration/test_ab_prompt_routes.py
import pytest
from backend.database import seed_system_config


@pytest.fixture
def seeded(test_session):
    seed_system_config(test_session)
    test_session.commit()


def test_ab_experiment_lifecycle(client, seeded):
    create = client.post("/api/v1/optimization/experiments", json={
        "name": "Resume A/B", "target_engine": "resume",
        "variant_a": {"template": "software"}, "variant_b": {"template": "modern"},
    })
    assert create.status_code == 200, create.text
    ids = create.json()["variant_ids"]
    a, b = ids["A"], ids["B"]

    # conclude with no data → 409
    exp_id = create.json()["experiment_id"]
    assert client.post(f"/api/v1/optimization/experiments/{exp_id}/conclude").status_code == 409

    for _ in range(3):
        client.post(f"/api/v1/optimization/experiments/variants/{a}/impression")
        client.post(f"/api/v1/optimization/experiments/variants/{b}/impression")
    client.post(f"/api/v1/optimization/experiments/variants/{b}/conversion")
    client.post(f"/api/v1/optimization/experiments/variants/{b}/conversion")

    concluded = client.post(f"/api/v1/optimization/experiments/{exp_id}/conclude")
    assert concluded.status_code == 200
    assert concluded.json()["winner_variant_id"] == b

    listing = client.get("/api/v1/optimization/experiments")
    assert listing.status_code == 200
    assert listing.json()["experiments"][0]["status"] == "concluded"


def test_prompt_seed_and_activate(client, seeded):
    seed = client.post("/api/v1/optimization/prompts/resume/generate/seed")
    assert seed.status_code == 200, seed.text
    assert seed.json()["is_active"] is True

    versions = client.get("/api/v1/optimization/prompts/resume/generate/versions")
    assert versions.status_code == 200
    vid = versions.json()["versions"][0]["id"]

    activate = client.post(f"/api/v1/optimization/prompts/versions/{vid}/activate")
    assert activate.status_code == 200
    assert activate.json()["is_active"] is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest backend/tests/integration/test_ab_prompt_routes.py -v --no-cov`
Expected: FAIL — 404s.

- [ ] **Step 3: Add the endpoints**

Append to `backend/api/v1/routes/optimization.py` (reuse the existing `router`, `get_session`, `HTTPException`):
```python
from pydantic import BaseModel
from backend.repositories.optimization import (
    ABExperimentRepository, ABVariantRepository, PromptVersionRepository,
)
from backend.services.optimization.ab_testing import ABTestingService
from backend.services.optimization.prompt_evolver import PromptEvolver


class CreateExperimentRequest(BaseModel):
    name: str
    target_engine: str
    variant_a: dict
    variant_b: dict


def _serialize_experiment(exp, variants, svc) -> dict:
    return {
        "id": exp.id, "name": exp.name, "target_engine": exp.target_engine,
        "metric": exp.metric, "status": exp.status,
        "winner_variant_id": exp.winner_variant_id,
        "created_at": exp.created_at, "concluded_at": exp.concluded_at,
        "variants": [
            {
                "id": v.id, "label": v.label,
                "impressions": v.impressions, "conversions": v.conversions,
                "conversion_rate": svc.conversion_rate(v.id),
            }
            for v in variants
        ],
    }


def _serialize_version(v) -> dict:
    return {
        "id": v.id, "prompt_name": v.prompt_name, "version": v.version,
        "is_active": v.is_active, "parent_version": v.parent_version,
        "change_rationale": v.change_rationale, "created_at": v.created_at,
    }


@router.post("/optimization/experiments")
def create_experiment(body: CreateExperimentRequest, session: Session = Depends(get_session)) -> dict:
    svc = ABTestingService(session)
    exp = svc.create_experiment(body.name, body.target_engine, body.variant_a, body.variant_b)
    variants = {v.label: v.id for v in ABVariantRepository(session).list_for_experiment(exp.id)}
    return {"experiment_id": exp.id, "variant_ids": variants}


@router.get("/optimization/experiments")
def list_experiments(session: Session = Depends(get_session)) -> dict:
    svc = ABTestingService(session)
    exp_repo = ABExperimentRepository(session)
    var_repo = ABVariantRepository(session)
    out = []
    for exp in exp_repo.list():
        out.append(_serialize_experiment(exp, var_repo.list_for_experiment(exp.id), svc))
    return {"experiments": out}


@router.post("/optimization/experiments/variants/{variant_id}/impression")
def record_impression(variant_id: str, session: Session = Depends(get_session)) -> dict:
    try:
        ABTestingService(session).record_impression(variant_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return {"ok": True}


@router.post("/optimization/experiments/variants/{variant_id}/conversion")
def record_conversion(variant_id: str, session: Session = Depends(get_session)) -> dict:
    try:
        ABTestingService(session).record_conversion(variant_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return {"ok": True}


@router.post("/optimization/experiments/{experiment_id}/conclude")
def conclude_experiment(experiment_id: str, session: Session = Depends(get_session)) -> dict:
    svc = ABTestingService(session)
    try:
        exp = svc.conclude(experiment_id)
    except ValueError as exc:
        msg = str(exc)
        code = 404 if "not found" in msg else 409
        raise HTTPException(status_code=code, detail=msg)
    variants = ABVariantRepository(session).list_for_experiment(exp.id)
    return _serialize_experiment(exp, variants, svc)


@router.get("/optimization/prompts/{prompt_name:path}/versions")
def list_prompt_versions(prompt_name: str, session: Session = Depends(get_session)) -> dict:
    repo = PromptVersionRepository(session)
    return {"versions": [_serialize_version(v) for v in repo.list_for_prompt(prompt_name)]}


@router.post("/optimization/prompts/{prompt_name:path}/seed")
def seed_prompt(prompt_name: str, session: Session = Depends(get_session)) -> dict:
    try:
        v = PromptEvolver(session).seed_from_disk(prompt_name)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return _serialize_version(v)


@router.post("/optimization/prompts/versions/{version_id}/activate")
def activate_prompt_version(version_id: str, session: Session = Depends(get_session)) -> dict:
    try:
        v = PromptEvolver(session).activate(version_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return _serialize_version(v)
```
**Routing note:** the `{prompt_name:path}/seed` and `{prompt_name:path}/versions` routes must be declared so they do not shadow `prompts/versions/{version_id}/activate`. Declare the `versions/{version_id}/activate` route BEFORE the `{prompt_name:path}` routes in the file, OR keep the literal `versions` segment distinct (it is, because activate uses `prompts/versions/...` while the path routes capture `prompts/<name>/...`). Verify with the test; if `activate` is shadowed, move its declaration above the `:path` routes.

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest backend/tests/integration/test_ab_prompt_routes.py -v --no-cov`
Expected: 2 passed. If `activate` returns 404 due to shadowing, reorder the route declarations as noted, then re-run.

- [ ] **Step 5: Commit**

```bash
git add backend/api/v1/routes/optimization.py backend/tests/integration/test_ab_prompt_routes.py
git commit -m "feat(optimization): add A/B experiment and prompt-version API endpoints"
```

---

### Task 14: Frontend optimization service + types

**Files:**
- Create: `frontend/src/services/optimization.ts`
- Test: `frontend/src/services/optimization.test.ts` (Vitest) — OR, if the repo has no frontend unit test runner, skip the test file and rely on `tsc --noEmit` (verify which by checking `frontend/package.json` scripts).

**Interfaces:**
- Consumes: `apiFetch<T>` and `ApiError` from `frontend/src/services/api.ts`.
- Produces typed client functions and interfaces:
  - `interface Proposal { id; target_engine; target_parameter; current_value: string | null; proposed_value; rationale; expected_impact; confidence_level; risk_level; evidence_json: string | null; status; created_at; updated_at; decided_at: string | null; }`
  - `interface OptimizationLog { id; proposal_id: string | null; action; target_engine; target_parameter; old_value: string | null; new_value: string | null; actor; created_at; }`
  - `interface ABVariant { id; label; impressions; conversions; conversion_rate; }`
  - `interface ABExperiment { id; name; target_engine; metric; status; winner_variant_id: string | null; created_at; concluded_at: string | null; variants: ABVariant[]; }`
  - `interface PromptVersion { id; prompt_name; version; is_active; parent_version: string | null; change_rationale: string | null; created_at; }`
  - Functions: `listProposals(status?)`, `generateProposals()`, `approveProposal(id)`, `rejectProposal(id)`, `applyProposal(id)`, `revertProposal(id)`, `listLogs(limit?)`, `runLoop()`, `listExperiments()`, `createExperiment(payload)`, `concludeExperiment(id)`, `listPromptVersions(name)`, `seedPrompt(name)`, `activatePromptVersion(id)`.

- [ ] **Step 1: Check the frontend test setup**

Run: `cat frontend/package.json | grep -A2 '"scripts"'`
Determine if `vitest` or `test` exists. If a test runner exists, write the Vitest test in Step 2; otherwise skip to Step 3 and verify via `tsc`.

- [ ] **Step 2: (If a runner exists) Write a minimal failing test**

```typescript
// frontend/src/services/optimization.test.ts
import { describe, it, expect, vi, beforeEach } from "vitest";
import * as api from "./api";
import { listProposals, approveProposal } from "./optimization";

describe("optimization service", () => {
  beforeEach(() => vi.restoreAllMocks());

  it("listProposals calls the proposals endpoint", async () => {
    const spy = vi.spyOn(api, "apiFetch").mockResolvedValue({ proposals: [] } as never);
    await listProposals("pending");
    expect(spy).toHaveBeenCalledWith("/optimization/proposals?status=pending");
  });

  it("approveProposal POSTs to the approve endpoint", async () => {
    const spy = vi.spyOn(api, "apiFetch").mockResolvedValue({} as never);
    await approveProposal("abc");
    expect(spy).toHaveBeenCalledWith(
      "/optimization/proposals/abc/approve",
      { method: "POST" },
    );
  });
});
```
Run: `cd frontend && npx vitest run src/services/optimization.test.ts` → FAIL (module missing).

- [ ] **Step 3: Write the service**

```typescript
// frontend/src/services/optimization.ts
import { apiFetch } from "./api";

export interface Proposal {
  id: string;
  target_engine: string;
  target_parameter: string;
  current_value: string | null;
  proposed_value: string;
  rationale: string;
  expected_impact: string;
  confidence_level: "verified" | "strong_inference" | "weak_inference";
  risk_level: "low" | "medium" | "high";
  evidence_json: string | null;
  status: "pending" | "approved" | "rejected" | "reverted";
  created_at: string;
  updated_at: string;
  decided_at: string | null;
}

export interface OptimizationLog {
  id: string;
  proposal_id: string | null;
  action: "applied" | "reverted";
  target_engine: string;
  target_parameter: string;
  old_value: string | null;
  new_value: string | null;
  actor: string;
  created_at: string;
}

export interface ABVariant {
  id: string;
  label: string;
  impressions: number;
  conversions: number;
  conversion_rate: number;
}

export interface ABExperiment {
  id: string;
  name: string;
  target_engine: string;
  metric: string;
  status: "running" | "concluded";
  winner_variant_id: string | null;
  created_at: string;
  concluded_at: string | null;
  variants: ABVariant[];
}

export interface PromptVersion {
  id: string;
  prompt_name: string;
  version: string;
  is_active: boolean;
  parent_version: string | null;
  change_rationale: string | null;
  created_at: string;
}

export async function listProposals(status?: string): Promise<Proposal[]> {
  const q = status ? `?status=${encodeURIComponent(status)}` : "";
  const data = await apiFetch<{ proposals: Proposal[] }>(`/optimization/proposals${q}`);
  return data.proposals;
}

export async function generateProposals(): Promise<{ created: number; proposal_ids: string[] }> {
  return apiFetch("/optimization/proposals/generate", { method: "POST" });
}

export async function approveProposal(id: string): Promise<Proposal> {
  return apiFetch(`/optimization/proposals/${id}/approve`, { method: "POST" });
}

export async function rejectProposal(id: string): Promise<Proposal> {
  return apiFetch(`/optimization/proposals/${id}/reject`, { method: "POST" });
}

export async function applyProposal(id: string): Promise<OptimizationLog> {
  return apiFetch(`/optimization/proposals/${id}/apply`, { method: "POST" });
}

export async function revertProposal(id: string): Promise<OptimizationLog> {
  return apiFetch(`/optimization/proposals/${id}/revert`, { method: "POST" });
}

export async function listLogs(limit = 50): Promise<OptimizationLog[]> {
  const data = await apiFetch<{ logs: OptimizationLog[] }>(`/optimization/logs?limit=${limit}`);
  return data.logs;
}

export async function runLoop(): Promise<{ ran: boolean; [k: string]: unknown }> {
  return apiFetch("/optimization/loop/run", { method: "POST" });
}

export async function listExperiments(): Promise<ABExperiment[]> {
  const data = await apiFetch<{ experiments: ABExperiment[] }>("/optimization/experiments");
  return data.experiments;
}

export async function createExperiment(payload: {
  name: string;
  target_engine: string;
  variant_a: Record<string, unknown>;
  variant_b: Record<string, unknown>;
}): Promise<{ experiment_id: string; variant_ids: Record<string, string> }> {
  return apiFetch("/optimization/experiments", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function concludeExperiment(id: string): Promise<ABExperiment> {
  return apiFetch(`/optimization/experiments/${id}/conclude`, { method: "POST" });
}

export async function listPromptVersions(name: string): Promise<PromptVersion[]> {
  const data = await apiFetch<{ versions: PromptVersion[] }>(
    `/optimization/prompts/${name}/versions`,
  );
  return data.versions;
}

export async function seedPrompt(name: string): Promise<PromptVersion> {
  return apiFetch(`/optimization/prompts/${name}/seed`, { method: "POST" });
}

export async function activatePromptVersion(id: string): Promise<PromptVersion> {
  return apiFetch(`/optimization/prompts/versions/${id}/activate`, { method: "POST" });
}
```

- [ ] **Step 4: Verify**

If a runner exists: `cd frontend && npx vitest run src/services/optimization.test.ts` → PASS.
Always: `cd frontend && npx tsc --noEmit` → no errors.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/services/optimization.ts frontend/src/services/optimization.test.ts
git commit -m "feat(frontend): add typed optimization API service"
```
(Omit the test file from `git add` if you skipped it.)

---
### Task 15: Optimization Review page (approval UI) + nav + route

**Files:**
- Create: `frontend/src/pages/OptimizationPage.tsx`
- Modify: `frontend/src/App.tsx` (lazy import + `<Route path="/optimization" .../>`)
- Modify: `frontend/src/layouts/AppShell.tsx` (add nav item)

**Interfaces:**
- Consumes: the service functions and `Proposal`/`OptimizationLog` types from `frontend/src/services/optimization.ts` (Task 14).
- Produces: a default-exported `OptimizationPage` React component that:
  - On mount, loads pending proposals (`listProposals("pending")`) and recent logs (`listLogs()`).
  - Has a "Generate Recommendations" button → `generateProposals()` then reloads.
  - Has a "Run Learning Loop" button → `runLoop()` then reloads.
  - Renders each proposal as a card showing: target engine, parameter, current → proposed value, rationale, expected impact, confidence badge, risk badge, and three buttons: **Approve**, **Reject**, and (only when `status === "approved"`) **Apply**. Applied proposals show a **Revert** button.
  - Confidence and risk render as colored badges (verified=green, strong_inference=blue, weak_inference=amber; risk low=green, medium=amber, high=red).
  - Shows an audit-log table at the bottom (action, parameter, old→new, timestamp).
  - All async handlers are wrapped in `void` and guarded with a try/catch that surfaces `ApiError.message` into an inline error banner.

- [ ] **Step 1: Write the page**

```tsx
// frontend/src/pages/OptimizationPage.tsx
import { useCallback, useEffect, useState } from "react";
import {
  listProposals, generateProposals, approveProposal, rejectProposal,
  applyProposal, revertProposal, listLogs, runLoop,
  type Proposal, type OptimizationLog,
} from "@/services/optimization";
import { ApiError } from "@/services/api";

const CONFIDENCE_STYLE: Record<string, string> = {
  verified: "bg-green-500/15 text-green-300",
  strong_inference: "bg-blue-500/15 text-blue-300",
  weak_inference: "bg-amber-500/15 text-amber-300",
};
const RISK_STYLE: Record<string, string> = {
  low: "bg-green-500/15 text-green-300",
  medium: "bg-amber-500/15 text-amber-300",
  high: "bg-red-500/15 text-red-300",
};

export default function OptimizationPage() {
  const [proposals, setProposals] = useState<Proposal[]>([]);
  const [logs, setLogs] = useState<OptimizationLog[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const reload = useCallback(async () => {
    const [p, l] = await Promise.all([listProposals(), listLogs()]);
    setProposals(p);
    setLogs(l);
  }, []);

  useEffect(() => { void reload().catch((e) => setError(String(e))); }, [reload]);

  const guard = async (fn: () => Promise<unknown>) => {
    setBusy(true); setError(null);
    try { await fn(); await reload(); }
    catch (e) { setError(e instanceof ApiError ? e.message : String(e)); }
    finally { setBusy(false); }
  };

  const active = proposals.filter((p) => p.status === "pending" || p.status === "approved");

  return (
    <div className="p-8 space-y-6 overflow-y-auto">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-neutral-50">Optimization</h1>
          <p className="text-sm text-neutral-400">
            Review proposed improvements. Nothing is applied without your approval.
          </p>
        </div>
        <div className="flex gap-2">
          <button disabled={busy} onClick={() => void guard(generateProposals)}
            className="px-3 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-sm disabled:opacity-50">
            Generate Recommendations
          </button>
          <button disabled={busy} onClick={() => void guard(runLoop)}
            className="px-3 py-2 rounded-lg bg-white/10 hover:bg-white/15 text-white text-sm disabled:opacity-50">
            Run Learning Loop
          </button>
        </div>
      </div>

      {error && (
        <div className="rounded-lg bg-red-500/10 border border-red-500/30 text-red-300 text-sm p-3">
          {error}
        </div>
      )}

      <div className="space-y-3">
        {active.length === 0 && (
          <p className="text-neutral-500 text-sm">No active proposals. Generate recommendations to begin.</p>
        )}
        {active.map((p) => (
          <div key={p.id} className="rounded-xl border border-white/10 bg-white/[0.03] p-4 space-y-2">
            <div className="flex items-center gap-2">
              <span className="text-xs uppercase tracking-wide text-neutral-400">{p.target_engine}</span>
              <span className="text-sm font-medium text-neutral-100">{p.target_parameter}</span>
              <span className={`ml-auto text-xs px-2 py-0.5 rounded ${CONFIDENCE_STYLE[p.confidence_level]}`}>
                {p.confidence_level}
              </span>
              <span className={`text-xs px-2 py-0.5 rounded ${RISK_STYLE[p.risk_level]}`}>
                risk: {p.risk_level}
              </span>
            </div>
            <div className="text-sm text-neutral-300">
              <span className="text-neutral-500">{p.current_value ?? "—"}</span>
              {" → "}
              <span className="text-neutral-100 font-medium">{p.proposed_value}</span>
            </div>
            <p className="text-sm text-neutral-300">{p.rationale}</p>
            <p className="text-xs text-neutral-400">Expected impact: {p.expected_impact}</p>
            <div className="flex gap-2 pt-1">
              {p.status === "pending" && (
                <>
                  <button disabled={busy} onClick={() => void guard(() => approveProposal(p.id))}
                    className="px-3 py-1.5 rounded-lg bg-green-600/80 hover:bg-green-600 text-white text-xs disabled:opacity-50">
                    Approve
                  </button>
                  <button disabled={busy} onClick={() => void guard(() => rejectProposal(p.id))}
                    className="px-3 py-1.5 rounded-lg bg-white/10 hover:bg-white/15 text-white text-xs disabled:opacity-50">
                    Reject
                  </button>
                </>
              )}
              {p.status === "approved" && (
                <>
                  <button disabled={busy} onClick={() => void guard(() => applyProposal(p.id))}
                    className="px-3 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-xs disabled:opacity-50">
                    Apply
                  </button>
                  <button disabled={busy} onClick={() => void guard(() => revertProposal(p.id))}
                    className="px-3 py-1.5 rounded-lg bg-white/10 hover:bg-white/15 text-white text-xs disabled:opacity-50">
                    Revert
                  </button>
                </>
              )}
            </div>
          </div>
        ))}
      </div>

      <div>
        <h2 className="text-sm font-semibold text-neutral-200 mb-2">Audit Log</h2>
        <div className="rounded-xl border border-white/10 overflow-hidden">
          <table className="w-full text-xs">
            <thead className="bg-white/[0.04] text-neutral-400">
              <tr>
                <th className="text-left px-3 py-2">Action</th>
                <th className="text-left px-3 py-2">Parameter</th>
                <th className="text-left px-3 py-2">Change</th>
                <th className="text-left px-3 py-2">When</th>
              </tr>
            </thead>
            <tbody>
              {logs.map((l) => (
                <tr key={l.id} className="border-t border-white/5 text-neutral-300">
                  <td className="px-3 py-2">{l.action}</td>
                  <td className="px-3 py-2">{l.target_parameter}</td>
                  <td className="px-3 py-2">{l.old_value ?? "—"} → {l.new_value ?? "—"}</td>
                  <td className="px-3 py-2 text-neutral-500">{l.created_at}</td>
                </tr>
              ))}
              {logs.length === 0 && (
                <tr><td colSpan={4} className="px-3 py-3 text-neutral-500">No changes recorded yet.</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Wire the route**

In `frontend/src/App.tsx`, add the lazy import beside the others:
```typescript
const OptimizationPage = lazy(() => import("@/pages/OptimizationPage"));
```
And add the route inside `<Routes>` (after `/learning`):
```tsx
<Route path="/optimization" element={<OptimizationPage />} />
```

- [ ] **Step 3: Add the nav item**

In `frontend/src/layouts/AppShell.tsx`, import an icon (e.g. `Wand2`) from `lucide-react` and add to `NAV_ITEMS` after the Learning Engine entry:
```typescript
{ to: "/optimization", label: "Optimization", icon: Wand2 },
```
(Add `Wand2` to the existing `lucide-react` import list.)

- [ ] **Step 4: Type-check**

Run: `cd frontend && npx tsc --noEmit`
Expected: no errors.

- [ ] **Step 5: Build the frontend**

Run: `cd frontend && npm run build`
Expected: build succeeds (Vite emits `dist/`).

- [ ] **Step 6: Commit**

```bash
git add frontend/src/pages/OptimizationPage.tsx frontend/src/App.tsx frontend/src/layouts/AppShell.tsx
git commit -m "feat(frontend): add Optimization review page with approval gate UI and audit log"
```

---

### Task 16: E2E optimization test, docs, and final validation

**Files:**
- Create: `backend/tests/integration/test_e2e_optimization.py`
- Create: `docs/OPTIMIZATION_SYSTEM.md`
- Modify: `CLAUDE.md` (note Phase 8 completion in the implementation status, if such a section exists; otherwise skip the CLAUDE.md edit)

**Interfaces:**
- Consumes: the full optimization stack via the FastAPI `client` fixture.
- Produces: one end-to-end test `test_optimization_full_cycle` that threads state across the whole loop, plus user-facing documentation.

- [ ] **Step 1: Write the E2E test**

```python
# backend/tests/integration/test_e2e_optimization.py
"""
End-to-end optimization cycle — single function, state-threaded.
Steps: seed outcomes → run loop → list pending proposal → approve → apply
       → verify config changed → revert → verify config restored → audit log.
No Ollama or ChromaDB required (the loop is pure metrics + proposals).
"""
import pytest
from backend.database import seed_system_config
from backend.repositories.outcome import OutcomeSignalRepository
from backend.repositories.system_config import SystemConfigRepository
from backend.services.learning.ranker import _SIGNAL_WEIGHTS
from backend.models.application import Application


@pytest.fixture
def seeded(test_session):
    seed_system_config(test_session)
    repo = OutcomeSignalRepository(test_session)
    # 5 strong template-A + 5 weak template-B → clear template proposal
    for sig, tpl, n in (("interview", "A", 5), ("no_response", "B", 5)):
        for _ in range(n):
            app = Application(company="C", position="P"); test_session.add(app); test_session.flush()
            repo.create(application_id=app.id, signal_type=sig,
                        signal_weight=_SIGNAL_WEIGHTS[sig], ats_score=70,
                        template_used=tpl, industry="ai")
    test_session.commit()


def test_optimization_full_cycle(client, seeded):
    # Step 1: learning loop fires (10 apps, trigger 5)
    loop = client.post("/api/v1/optimization/loop/run")
    assert loop.status_code == 200 and loop.json()["ran"] is True

    # Step 2: a pending template proposal exists
    pending = client.get("/api/v1/optimization/proposals?status=pending").json()["proposals"]
    template_props = [p for p in pending if p["target_parameter"] == "default_template"]
    assert template_props, "expected a default_template proposal"
    pid = template_props[0]["id"]
    assert template_props[0]["proposed_value"] == "A"   # A had the strong signals

    # Step 3: apply is blocked before approval (guardrail)
    assert client.post(f"/api/v1/optimization/proposals/{pid}/apply").status_code == 409

    # Step 4: approve → apply → config changed
    assert client.post(f"/api/v1/optimization/proposals/{pid}/approve").status_code == 200
    applied = client.post(f"/api/v1/optimization/proposals/{pid}/apply")
    assert applied.status_code == 200 and applied.json()["new_value"] == "A"

    # Step 5: revert → config restored, proposal marked reverted
    rev = client.post(f"/api/v1/optimization/proposals/{pid}/revert")
    assert rev.status_code == 200 and rev.json()["action"] == "reverted"

    # Step 6: audit log holds both apply and revert (immutable trail)
    actions = {l["action"] for l in client.get("/api/v1/optimization/logs").json()["logs"]}
    assert {"applied", "reverted"} <= actions
```

- [ ] **Step 2: Run the E2E test**

Run: `.venv/bin/python -m pytest backend/tests/integration/test_e2e_optimization.py -v --no-cov`
Expected: 1 passed.

- [ ] **Step 3: Run the full backend suite (no regressions)**

Run: `.venv/bin/python -m pytest backend/tests -q`
Expected: all pass (coverage gate may apply; if the suite enforces ≥90%, ensure new modules are exercised by the unit tests written in Tasks 1–16).

- [ ] **Step 4: Write the documentation**

Create `docs/OPTIMIZATION_SYSTEM.md` (≥80 lines) covering, accurately to the implementation:
- **Overview & safety model** — the four invariants (logged, explainable, reversible, approval-gated); "interview rate, not ATS score" as primary objective.
- **Data model** — `optimization_proposals`, `optimization_logs` (append-only), `prompt_versions`, `ab_experiments`, `ab_variants`.
- **The loop** — Evaluator metrics → Recommender heuristics → pending proposals; fires every `learning_trigger_count` applications.
- **Approval workflow** — pending → approved → applied → (reverted); apply refused unless approved (HTTP 409).
- **Explainability fields** — what changed / why / expected impact / confidence / risk, with the three confidence levels and three risk levels.
- **A/B testing** — variants scored on interview conversion rate; conclude requires data.
- **Prompt versioning** — versioned, never overwritten; activate enforces single active version; revert = re-activate prior.
- **API reference** — table of every `/optimization/...` endpoint with method + purpose (mirror Tasks 12–13).
- **Guardrails** — the exact rejection rules from Task 6.

- [ ] **Step 5: Commit**

```bash
git add backend/tests/integration/test_e2e_optimization.py docs/OPTIMIZATION_SYSTEM.md
git commit -m "test(optimization): add E2E optimization cycle test; docs: add OPTIMIZATION_SYSTEM guide"
```

- [ ] **Step 6: Tag the release**

```bash
git tag -a v0.2.0 -m "Phase 8 complete: controlled autonomous optimization system — proposals, approval gate, A/B testing, prompt versioning, learning loop"
git commit --allow-empty -m "release(v0.2.0): Phase 8 — controlled autonomous optimization system"
```

---

## Self-Review

**Spec coverage:**
- §1 Optimization Targets (resume/ats/rag/cover_letter/copilot) → engine enum in Task 1; proposals target any engine. RAG/copilot/cover_letter are tunable via config-key proposals (same Applier path).
- §2 Feedback Signals (strong/weak) → `STRONG_SIGNALS`/`WEAK_SIGNALS` in Task 5; interview rate built on strong signals.
- §3 Optimization Engine (capture/compute/store) → Evaluator (Task 5) + proposals dataset (Task 1).
- §4 Recommendation System (propose, never auto-apply) → Recommender (Task 7) creates only `pending`; Applier gate (Task 8).
- §5 Prompt Evolution (versioned/explainable/reversible) → PromptVersion (Task 3) + PromptEvolver (Task 9).
- §6 Learning Loop every 5 applications → LearningLoop (Task 11), trigger from config.
- §7 A/B Testing on interview conversion → ABTestingService (Task 10) + routes (Task 13).
- §8 Guardrails (logging, no deletion, versioning, not ATS-only) → guardrails (Task 6), append-only log (Task 2), PromptVersion retention (Task 3).
- §9 Explainability (what/why/impact/confidence/risk) → required fields enforced in Tasks 1 & 6.
- Deliverables (engine, A/B, loop, prompt versioning, tunable system, approval gates) → Tasks 7–16.

**Placeholder scan:** none — every step has concrete code or commands.

**Type consistency:** repository attribute is `self.session` throughout (matches `BaseRepository`); `generate_uuid`/`utcnow` imported from `backend.models.base`; engine enum identical across models, guardrails, and recommender; route prefix mounting matches existing `app.include_router(..., prefix="/api/v1")` convention.
