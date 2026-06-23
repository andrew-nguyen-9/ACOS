# Phase 4: Intelligence + Interaction Layer — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add the Career Copilot (RAG chat), Application CRM CRUD API, Learning Engine (outcome-based ranking), and Question/Answer generation system to ACOS.

**Architecture:** All four subsystems layer on top of Phase 3's existing models (Application, Question, Answer, OutcomeSignal, Resume are all already SQLAlchemy-registered). The Learning Engine feeds from CRM outcomes; the Copilot queries the same RAGService used in Phase 2; Q&A draws evidence from the same EvidenceSelector used by the resume generator. No new Alembic migrations are needed — `init_db()` already calls `Base.metadata.create_all()`.

**Tech Stack:** FastAPI + SQLAlchemy 2.0 + Pydantic v2 + existing RAGService/EvidenceSelector/OllamaClient from Phases 2–3.

## Global Constraints

- Python venv at `.venv/` — always `source .venv/bin/activate` before commands.
- `from __future__ import annotations` at top of every new Python file.
- UUID PKs: `uuid.uuid4().hex` — String(32), no hyphens. (Default is on the model via `generate_uuid`; repos don't pass it.)
- Timestamps: `datetime.utcnow().isoformat()` — String(32). (Default via `utcnow` on model.)
- `BaseRepository.create(**kwargs)` — takes keyword arguments, NOT a model instance.
- Confidence levels: only `"verified"`, `"strong_inference"`, `"weak_inference"` — never any other value.
- `weak_inference` content → `requires_approval: True` in API responses.
- Duck-typed service collaborators → `from typing import Any` with a justification comment.
- Settings parameter type: `from backend.config import Settings` (not `Any`).
- Tests: unit tests use `test_session` fixture; integration tests use `client` fixture.
- All new services must degrade gracefully when Ollama is unavailable (use `ollama.is_available()` guard).
- Coverage gate: ≥90% at end of Task 8.
- No hallucination: never invent metrics, employers, or projects in generated content.

---

## File Structure

```
backend/
  api/v1/routes/
    application.py         NEW — CRM API: 7 endpoints
    questions.py           NEW — Q&A API: 5 endpoints
    learning.py            NEW — Learning API: 3 endpoints
    copilot.py             NEW — Copilot API: 2 endpoints
  repositories/
    question.py            NEW — QuestionRepository, AnswerRepository
    outcome.py             NEW — OutcomeSignalRepository
    __init__.py            MODIFY — export new repos
  services/
    copilot/
      __init__.py          NEW (empty)
      engine.py            NEW — CopilotEngine
    learning/
      __init__.py          NEW (empty)
      ranker.py            NEW — OutcomeRanker
    questions/
      __init__.py          NEW (empty)
      generator.py         NEW — QuestionGenerator
  prompts/
    copilot/
      chat.yaml            NEW
    questions/
      generate.yaml        NEW
      answer.yaml          NEW
  main.py                  MODIFY — register 4 new routers
tests/
  unit/
    test_question_generator.py   NEW
    test_outcome_ranker.py       NEW
    test_copilot_engine.py       NEW
  integration/
    test_application_routes.py   NEW
    test_question_routes.py      NEW
    test_learning_routes.py      NEW
    test_copilot_routes.py       NEW
```

---

### Task 1: Application CRM API

**Files:**
- Create: `backend/api/v1/routes/application.py`
- Create: `backend/tests/integration/test_application_routes.py`
- Modify: `backend/main.py` (add application router)

**Interfaces:**
- Consumes: `ApplicationRepository` from `backend/repositories/application.py` — already implemented.
  - `repo.get(id)`, `repo.list()`, `repo.create(**kwargs)`, `repo.delete(id)`, `repo.count()`
  - `repo.get_by_status(status) -> list[Application]`
  - `repo.transition_status(application_id, new_status) -> Application | None`
  - `repo.record_timeline_event(application_id, event_type, from_status, to_status, note) -> ApplicationTimeline`
  - `app.timeline` — relationship, list of `ApplicationTimeline` objects
- Produces: routers at `/api/v1/applications/*` consumed by Task 6 (learning outcome endpoint links application_id).

- [ ] **Step 1: Write the failing integration tests**

```python
# backend/tests/integration/test_application_routes.py
from __future__ import annotations


def test_create_application(client):
    resp = client.post("/api/v1/applications", json={"company": "Acme", "position": "Engineer"})
    assert resp.status_code == 201
    data = resp.json()
    assert data["company"] == "Acme"
    assert data["status"] == "draft"
    assert "id" in data
    assert "created_at" in data


def test_list_applications_empty(client):
    resp = client.get("/api/v1/applications")
    assert resp.status_code == 200
    assert resp.json() == []


def test_list_applications_filter_by_status(client):
    client.post("/api/v1/applications", json={"company": "A", "position": "P1", "status": "applied"})
    client.post("/api/v1/applications", json={"company": "B", "position": "P2", "status": "draft"})
    resp = client.get("/api/v1/applications?status=applied")
    assert resp.status_code == 200
    result = resp.json()
    assert len(result) == 1
    assert result[0]["company"] == "A"


def test_get_application(client):
    create = client.post("/api/v1/applications", json={"company": "Z", "position": "Dev"})
    app_id = create.json()["id"]
    resp = client.get(f"/api/v1/applications/{app_id}")
    assert resp.status_code == 200
    assert resp.json()["id"] == app_id
    assert resp.json()["company"] == "Z"


def test_get_application_not_found(client):
    resp = client.get("/api/v1/applications/doesnotexist")
    assert resp.status_code == 404


def test_update_status(client):
    create = client.post("/api/v1/applications", json={"company": "X", "position": "Y"})
    app_id = create.json()["id"]
    resp = client.patch(f"/api/v1/applications/{app_id}/status", json={"status": "applied"})
    assert resp.status_code == 200
    assert resp.json()["status"] == "applied"


def test_update_status_invalid(client):
    create = client.post("/api/v1/applications", json={"company": "X", "position": "Y"})
    app_id = create.json()["id"]
    resp = client.patch(f"/api/v1/applications/{app_id}/status", json={"status": "hired"})
    assert resp.status_code == 422


def test_update_status_not_found(client):
    resp = client.patch("/api/v1/applications/doesnotexist/status", json={"status": "applied"})
    assert resp.status_code == 404


def test_add_note(client):
    create = client.post("/api/v1/applications", json={"company": "X", "position": "Y"})
    app_id = create.json()["id"]
    resp = client.post(f"/api/v1/applications/{app_id}/notes", json={"note": "Looks promising"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["event_type"] == "note_added"
    assert data["note"] == "Looks promising"


def test_add_note_not_found(client):
    resp = client.post("/api/v1/applications/doesnotexist/notes", json={"note": "test"})
    assert resp.status_code == 404


def test_get_timeline(client):
    create = client.post("/api/v1/applications", json={"company": "X", "position": "Y"})
    app_id = create.json()["id"]
    client.patch(f"/api/v1/applications/{app_id}/status", json={"status": "applied"})
    resp = client.get(f"/api/v1/applications/{app_id}/timeline")
    assert resp.status_code == 200
    events = resp.json()
    assert any(e["event_type"] == "status_change" for e in events)
    assert any(e["to_status"] == "applied" for e in events)


def test_get_timeline_not_found(client):
    resp = client.get("/api/v1/applications/doesnotexist/timeline")
    assert resp.status_code == 404


def test_delete_application(client):
    create = client.post("/api/v1/applications", json={"company": "X", "position": "Y"})
    app_id = create.json()["id"]
    resp = client.delete(f"/api/v1/applications/{app_id}")
    assert resp.status_code == 204
    assert client.get(f"/api/v1/applications/{app_id}").status_code == 404


def test_delete_application_not_found(client):
    resp = client.delete("/api/v1/applications/doesnotexist")
    assert resp.status_code == 404


def test_create_application_invalid_status(client):
    resp = client.post("/api/v1/applications", json={"company": "A", "position": "B", "status": "hired"})
    assert resp.status_code == 422


def test_create_application_invalid_source(client):
    resp = client.post("/api/v1/applications", json={"company": "A", "position": "B", "source": "twitter"})
    assert resp.status_code == 422


def test_create_application_invalid_work_arrangement(client):
    resp = client.post("/api/v1/applications", json={"company": "A", "position": "B", "work_arrangement": "moon"})
    assert resp.status_code == 422
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
source .venv/bin/activate && pytest backend/tests/integration/test_application_routes.py -v 2>&1 | head -30
```
Expected: ImportError or 404s (router not registered yet).

- [ ] **Step 3: Implement the Application CRM API route**

```python
# backend/api/v1/routes/application.py
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.database import get_session
from backend.repositories.application import ApplicationRepository

router = APIRouter(tags=["applications"])

_VALID_STATUSES = {
    "draft", "applied", "phone_screen", "interview",
    "final_round", "offer", "rejected", "withdrawn",
}
_VALID_SOURCES = {"linkedin", "indeed", "referral", "direct", "recruiter", "other"}
_VALID_ARRANGEMENTS = {"remote", "hybrid", "onsite"}


class CreateApplicationRequest(BaseModel):
    company: str
    position: str
    industry: str | None = None
    job_description: str | None = None
    job_url: str | None = None
    status: str = "draft"
    date_applied: str | None = None
    salary_min: int | None = None
    salary_max: int | None = None
    currency: str = "USD"
    work_arrangement: str | None = None
    source: str | None = None
    recruiter_name: str | None = None
    recruiter_email: str | None = None
    notes: str | None = None


class UpdateStatusRequest(BaseModel):
    status: str


class AddNoteRequest(BaseModel):
    note: str


@router.post("/applications", status_code=201)
def create_application(
    body: CreateApplicationRequest, session: Session = Depends(get_session)
) -> dict:
    if body.status not in _VALID_STATUSES:
        raise HTTPException(status_code=422, detail=f"Invalid status '{body.status}'")
    if body.work_arrangement and body.work_arrangement not in _VALID_ARRANGEMENTS:
        raise HTTPException(
            status_code=422, detail=f"Invalid work_arrangement '{body.work_arrangement}'"
        )
    if body.source and body.source not in _VALID_SOURCES:
        raise HTTPException(status_code=422, detail=f"Invalid source '{body.source}'")
    repo = ApplicationRepository(session)
    app = repo.create(
        company=body.company,
        position=body.position,
        industry=body.industry,
        job_description=body.job_description,
        job_url=body.job_url,
        status=body.status,
        date_applied=body.date_applied,
        salary_min=body.salary_min,
        salary_max=body.salary_max,
        currency=body.currency,
        work_arrangement=body.work_arrangement,
        source=body.source,
        recruiter_name=body.recruiter_name,
        recruiter_email=body.recruiter_email,
        notes=body.notes,
    )
    return {
        "id": app.id,
        "company": app.company,
        "position": app.position,
        "status": app.status,
        "created_at": app.created_at,
    }


@router.get("/applications")
def list_applications(
    status: str | None = None, session: Session = Depends(get_session)
) -> list[dict]:
    repo = ApplicationRepository(session)
    apps = repo.get_by_status(status) if status else repo.list()
    return [
        {
            "id": a.id,
            "company": a.company,
            "position": a.position,
            "status": a.status,
            "date_applied": a.date_applied,
            "created_at": a.created_at,
        }
        for a in apps
    ]


@router.get("/applications/{application_id}")
def get_application(
    application_id: str, session: Session = Depends(get_session)
) -> dict:
    repo = ApplicationRepository(session)
    app = repo.get(application_id)
    if app is None:
        raise HTTPException(status_code=404, detail="Application not found")
    return {
        "id": app.id,
        "company": app.company,
        "position": app.position,
        "industry": app.industry,
        "job_description": app.job_description,
        "job_url": app.job_url,
        "status": app.status,
        "date_applied": app.date_applied,
        "salary_min": app.salary_min,
        "salary_max": app.salary_max,
        "currency": app.currency,
        "work_arrangement": app.work_arrangement,
        "source": app.source,
        "recruiter_name": app.recruiter_name,
        "recruiter_email": app.recruiter_email,
        "notes": app.notes,
        "created_at": app.created_at,
        "updated_at": app.updated_at,
    }


@router.patch("/applications/{application_id}/status")
def update_status(
    application_id: str,
    body: UpdateStatusRequest,
    session: Session = Depends(get_session),
) -> dict:
    if body.status not in _VALID_STATUSES:
        raise HTTPException(status_code=422, detail=f"Invalid status '{body.status}'")
    repo = ApplicationRepository(session)
    app = repo.transition_status(application_id, body.status)
    if app is None:
        raise HTTPException(status_code=404, detail="Application not found")
    return {"id": app.id, "status": app.status}


@router.post("/applications/{application_id}/notes")
def add_note(
    application_id: str,
    body: AddNoteRequest,
    session: Session = Depends(get_session),
) -> dict:
    repo = ApplicationRepository(session)
    if repo.get(application_id) is None:
        raise HTTPException(status_code=404, detail="Application not found")
    event = repo.record_timeline_event(
        application_id=application_id,
        event_type="note_added",
        note=body.note,
    )
    return {
        "id": event.id,
        "event_type": event.event_type,
        "note": event.note,
        "event_date": event.event_date,
    }


@router.get("/applications/{application_id}/timeline")
def get_timeline(
    application_id: str, session: Session = Depends(get_session)
) -> list[dict]:
    repo = ApplicationRepository(session)
    app = repo.get(application_id)
    if app is None:
        raise HTTPException(status_code=404, detail="Application not found")
    return [
        {
            "id": e.id,
            "event_type": e.event_type,
            "from_status": e.from_status,
            "to_status": e.to_status,
            "note": e.note,
            "event_date": e.event_date,
        }
        for e in app.timeline
    ]


@router.delete("/applications/{application_id}", status_code=204)
def delete_application(
    application_id: str, session: Session = Depends(get_session)
) -> None:
    repo = ApplicationRepository(session)
    if not repo.delete(application_id):
        raise HTTPException(status_code=404, detail="Application not found")
```

- [ ] **Step 4: Register the router in main.py**

In `backend/main.py`, add after the existing imports and `include_router` calls:

```python
# Add import at the top with the other route imports:
from backend.api.v1.routes.application import router as application_router

# Add inside create_app(), after the existing include_router calls:
app.include_router(application_router, prefix="/api/v1")
```

- [ ] **Step 5: Run the tests and verify they pass**

```bash
source .venv/bin/activate && pytest backend/tests/integration/test_application_routes.py -v
```
Expected: all 17 tests PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/api/v1/routes/application.py backend/tests/integration/test_application_routes.py backend/main.py
git commit -m "feat: add Application CRM API with status lifecycle and timeline"
```

---

### Task 2: Q&A + Outcome Signal Repositories

**Files:**
- Create: `backend/repositories/question.py`
- Create: `backend/repositories/outcome.py`
- Modify: `backend/repositories/__init__.py`

**Interfaces:**
- Consumes: `Question`, `Answer` from `backend/models/question.py`; `OutcomeSignal` from `backend/models/outcome.py`; `BaseRepository` from `backend/repositories/base.py`.
- Produces:
  - `QuestionRepository(session).get_by_category(category) -> list[Question]`
  - `QuestionRepository(session).get_by_source(source) -> list[Question]`
  - `AnswerRepository(session).get_by_question(question_id) -> list[Answer]`
  - `AnswerRepository(session).get_by_application(application_id) -> list[Answer]`
  - `AnswerRepository(session).get_latest(question_id) -> Answer | None`
  - `OutcomeSignalRepository(session).get_by_application(application_id) -> list[OutcomeSignal]`
  - `OutcomeSignalRepository(session).get_by_resume(resume_id) -> list[OutcomeSignal]`
  - `OutcomeSignalRepository(session).get_by_signal_type(signal_type) -> list[OutcomeSignal]`

- [ ] **Step 1: Write failing unit tests**

```python
# backend/tests/unit/test_repositories.py  (append to or create new file)
# Use backend/tests/unit/test_question_outcome_repositories.py
from __future__ import annotations

import pytest
from backend.repositories.question import QuestionRepository, AnswerRepository
from backend.repositories.outcome import OutcomeSignalRepository
from backend.repositories.application import ApplicationRepository


def _make_question(session, template="Tell me about {{company}}.", category="behavioral"):
    repo = QuestionRepository(session)
    return repo.create(
        question_template=template,
        category=category,
        length_target="medium",
        variables=["company"],
        source="generated",
    )


def _make_app(session):
    repo = ApplicationRepository(session)
    return repo.create(company="Acme", position="Engineer")


def test_question_repo_get_by_category(test_session):
    _make_question(test_session, category="behavioral")
    _make_question(test_session, category="technical")
    repo = QuestionRepository(test_session)
    behavioral = repo.get_by_category("behavioral")
    assert len(behavioral) == 1
    assert behavioral[0].category == "behavioral"


def test_question_repo_get_by_source(test_session):
    repo = QuestionRepository(test_session)
    repo.create(
        question_template="Manual question", category="behavioral",
        length_target="medium", variables=[], source="manual",
    )
    _make_question(test_session)  # source="generated"
    manual = repo.get_by_source("manual")
    assert len(manual) == 1


def test_answer_repo_get_by_question(test_session):
    q = _make_question(test_session)
    a_repo = AnswerRepository(test_session)
    a_repo.create(
        question_id=q.id,
        original_answer="My answer",
        confidence_level="verified",
        evidence_ids=[],
    )
    answers = a_repo.get_by_question(q.id)
    assert len(answers) == 1
    assert answers[0].original_answer == "My answer"


def test_answer_repo_get_by_application(test_session):
    q = _make_question(test_session)
    app = _make_app(test_session)
    a_repo = AnswerRepository(test_session)
    a_repo.create(
        question_id=q.id,
        application_id=app.id,
        original_answer="Context answer",
        confidence_level="strong_inference",
        evidence_ids=[],
    )
    answers = a_repo.get_by_application(app.id)
    assert len(answers) == 1


def test_answer_repo_get_latest(test_session):
    q = _make_question(test_session)
    a_repo = AnswerRepository(test_session)
    a_repo.create(
        question_id=q.id, original_answer="First", confidence_level="verified", evidence_ids=[]
    )
    a_repo.create(
        question_id=q.id, original_answer="Second", confidence_level="verified", evidence_ids=[]
    )
    latest = a_repo.get_latest(q.id)
    assert latest is not None


def test_answer_repo_get_latest_no_answers(test_session):
    q = _make_question(test_session)
    a_repo = AnswerRepository(test_session)
    assert a_repo.get_latest(q.id) is None


def test_outcome_signal_repo_get_by_application(test_session):
    app = _make_app(test_session)
    repo = OutcomeSignalRepository(test_session)
    repo.create(application_id=app.id, signal_type="interview", signal_weight=0.7)
    results = repo.get_by_application(app.id)
    assert len(results) == 1
    assert results[0].signal_type == "interview"


def test_outcome_signal_repo_get_by_signal_type(test_session):
    app1 = _make_app(test_session)
    app2 = ApplicationRepository(test_session).create(company="B", position="P")
    repo = OutcomeSignalRepository(test_session)
    repo.create(application_id=app1.id, signal_type="offer", signal_weight=1.0)
    repo.create(application_id=app2.id, signal_type="rejected", signal_weight=0.1)
    offers = repo.get_by_signal_type("offer")
    assert len(offers) == 1
    assert offers[0].signal_type == "offer"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
source .venv/bin/activate && pytest backend/tests/unit/test_question_outcome_repositories.py -v 2>&1 | head -20
```
Expected: ImportError — modules don't exist yet.

- [ ] **Step 3: Implement QuestionRepository and AnswerRepository**

```python
# backend/repositories/question.py
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models.question import Answer, Question
from backend.repositories.base import BaseRepository


class QuestionRepository(BaseRepository[Question]):
    def __init__(self, session: Session) -> None:
        super().__init__(Question, session)

    def get_by_category(self, category: str) -> list[Question]:
        return list(
            self.session.scalars(
                select(Question).where(Question.category == category)
            ).all()
        )

    def get_by_source(self, source: str) -> list[Question]:
        return list(
            self.session.scalars(
                select(Question).where(Question.source == source)
            ).all()
        )


class AnswerRepository(BaseRepository[Answer]):
    def __init__(self, session: Session) -> None:
        super().__init__(Answer, session)

    def get_by_question(self, question_id: str) -> list[Answer]:
        return list(
            self.session.scalars(
                select(Answer).where(Answer.question_id == question_id)
            ).all()
        )

    def get_by_application(self, application_id: str) -> list[Answer]:
        return list(
            self.session.scalars(
                select(Answer).where(Answer.application_id == application_id)
            ).all()
        )

    def get_latest(self, question_id: str) -> Answer | None:
        results = list(
            self.session.scalars(
                select(Answer)
                .where(Answer.question_id == question_id)
                .order_by(Answer.created_at.desc())
                .limit(1)
            ).all()
        )
        return results[0] if results else None
```

- [ ] **Step 4: Implement OutcomeSignalRepository**

```python
# backend/repositories/outcome.py
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models.outcome import OutcomeSignal
from backend.repositories.base import BaseRepository


class OutcomeSignalRepository(BaseRepository[OutcomeSignal]):
    def __init__(self, session: Session) -> None:
        super().__init__(OutcomeSignal, session)

    def get_by_application(self, application_id: str) -> list[OutcomeSignal]:
        return list(
            self.session.scalars(
                select(OutcomeSignal).where(OutcomeSignal.application_id == application_id)
            ).all()
        )

    def get_by_resume(self, resume_id: str) -> list[OutcomeSignal]:
        return list(
            self.session.scalars(
                select(OutcomeSignal).where(OutcomeSignal.resume_id == resume_id)
            ).all()
        )

    def get_by_signal_type(self, signal_type: str) -> list[OutcomeSignal]:
        return list(
            self.session.scalars(
                select(OutcomeSignal).where(OutcomeSignal.signal_type == signal_type)
            ).all()
        )
```

- [ ] **Step 5: Update repositories __init__.py**

Replace the entire content of `backend/repositories/__init__.py`:

```python
from backend.repositories.base import BaseRepository
from backend.repositories.experience import ExperienceRepository
from backend.repositories.skill import SkillRepository
from backend.repositories.application import ApplicationRepository
from backend.repositories.document import DocumentRepository
from backend.repositories.system_config import SystemConfigRepository
from backend.repositories.knowledge_graph import (
    KnowledgeGraphNodeRepository,
    KnowledgeGraphEdgeRepository,
)
from backend.repositories.question import QuestionRepository, AnswerRepository
from backend.repositories.outcome import OutcomeSignalRepository

__all__ = [
    "BaseRepository",
    "ExperienceRepository",
    "SkillRepository",
    "ApplicationRepository",
    "DocumentRepository",
    "SystemConfigRepository",
    "KnowledgeGraphNodeRepository",
    "KnowledgeGraphEdgeRepository",
    "QuestionRepository",
    "AnswerRepository",
    "OutcomeSignalRepository",
]
```

- [ ] **Step 6: Run tests to verify they pass**

```bash
source .venv/bin/activate && pytest backend/tests/unit/test_question_outcome_repositories.py -v
```
Expected: all 9 tests PASS.

- [ ] **Step 7: Commit**

```bash
git add backend/repositories/question.py backend/repositories/outcome.py backend/repositories/__init__.py backend/tests/unit/test_question_outcome_repositories.py
git commit -m "feat: add QuestionRepository, AnswerRepository, OutcomeSignalRepository"
```

---

### Task 3: Question Generator + Prompts

**Files:**
- Create: `backend/services/questions/__init__.py`
- Create: `backend/services/questions/generator.py`
- Create: `backend/prompts/questions/generate.yaml`
- Create: `backend/prompts/questions/answer.yaml`
- Create: `backend/tests/unit/test_question_generator.py`

**Interfaces:**
- Consumes:
  - `OllamaClient` (Any duck-type): `.is_available() -> bool`, `.generate(model, prompt, system, temperature) -> str`
  - `PromptLoader` (Any duck-type): `.load(name: str) -> dict` with `{version, system, user_template}`; name uses slash notation e.g. `"questions/generate"`
  - `EvidenceSelector` (Any duck-type): `.select(job_description, keywords, max_bullets) -> list[dict]` where each dict has `{bullet_text, evidence_id, confidence}`
  - `QuestionRepository`, `AnswerRepository` from Task 2
- Produces:
  - `QuestionGenerator(ollama, loader, selector, session)`
  - `.generate_questions(job_description, company, position, industry, tech_stack, application_id) -> list[dict]`
    - Returns `[{id, question_template, interpolated, category, variables}]`
  - `.generate_answer(question_id, variables, application_id, length_target) -> dict`
    - Returns `{answer_id, question_id, interpolated_question, original_answer, evidence_ids, confidence_level, requires_approval}`
    - Raises `ValueError("Invalid length_target '...'")` if not in `{"short","medium","long"}`
    - Raises `ValueError("Question not found: ...")` if question_id missing
  - `.edit_answer(answer_id, edited_text, diff_summary) -> dict`
    - Returns `{answer_id, original_answer, edited_answer, diff_summary}`
    - Raises `ValueError("Answer not found: ...")` if answer_id missing
  - `_interpolate(template, variables) -> str` — module-level function, replaces `{{var}}` placeholders

- [ ] **Step 1: Write failing unit tests**

```python
# backend/tests/unit/test_question_generator.py
from __future__ import annotations

import pytest
from unittest.mock import MagicMock

from backend.services.questions.generator import QuestionGenerator, _interpolate


def _make_generator(session, ollama=None, loader=None, selector=None):
    if ollama is None:
        ollama = MagicMock()
        ollama.is_available.return_value = False
    if loader is None:
        loader = MagicMock()
    if selector is None:
        selector = MagicMock()
        selector.select.return_value = []
    return QuestionGenerator(ollama, loader, selector, session)


def test_interpolate_replaces_variables():
    result = _interpolate("Tell me about {{company}} as a {{position}}.", {"company": "Acme", "position": "Engineer"})
    assert result == "Tell me about Acme as a Engineer."


def test_interpolate_leaves_unknown_variables():
    result = _interpolate("What is {{unknown}}?", {})
    assert result == "What is {{unknown}}?"


def test_interpolate_empty_template():
    assert _interpolate("", {"company": "A"}) == ""


def test_generate_questions_fallback_when_ollama_unavailable(test_session):
    gen = _make_generator(test_session)
    results = gen.generate_questions(
        "Python developer role at Acme", company="Acme", position="Dev"
    )
    assert isinstance(results, list)
    assert len(results) > 0
    for q in results:
        assert "id" in q
        assert "question_template" in q
        assert "interpolated" in q
        assert "category" in q
        assert "variables" in q


def test_generate_questions_stores_in_db(test_session):
    gen = _make_generator(test_session)
    results = gen.generate_questions("Role description", company="Foo", position="Bar")
    from backend.repositories.question import QuestionRepository
    repo = QuestionRepository(test_session)
    assert repo.count() == len(results)


def test_generate_questions_interpolates_variables(test_session):
    gen = _make_generator(test_session)
    results = gen.generate_questions(
        "Dev role", company="Acme", position="Engineer", industry="Tech"
    )
    for q in results:
        assert "{{company}}" not in q["interpolated"]
        assert "{{position}}" not in q["interpolated"]


def test_generate_answer_invalid_length(test_session):
    gen = _make_generator(test_session)
    with pytest.raises(ValueError, match="Invalid length_target"):
        gen.generate_answer("any-id", {}, length_target="xl")


def test_generate_answer_question_not_found(test_session):
    gen = _make_generator(test_session)
    with pytest.raises(ValueError, match="Question not found"):
        gen.generate_answer("doesnotexist", {})


def test_generate_answer_stores_in_db(test_session):
    gen = _make_generator(test_session)
    questions = gen.generate_questions("Dev role", company="Acme", position="Dev")
    q_id = questions[0]["id"]
    result = gen.generate_answer(q_id, {"company": "Acme", "position": "Dev"})
    assert "answer_id" in result
    assert "original_answer" in result
    assert result["confidence_level"] in ("verified", "strong_inference", "weak_inference")
    assert isinstance(result["requires_approval"], bool)


def test_generate_answer_requires_approval_for_weak_inference(test_session):
    selector = MagicMock()
    selector.select.return_value = []  # no evidence → weak_inference
    gen = _make_generator(test_session, selector=selector)
    questions = gen.generate_questions("Dev role")
    q_id = questions[0]["id"]
    result = gen.generate_answer(q_id, {})
    assert result["requires_approval"] is True
    assert result["confidence_level"] == "weak_inference"


def test_edit_answer(test_session):
    gen = _make_generator(test_session)
    questions = gen.generate_questions("Dev role")
    q_id = questions[0]["id"]
    answer_result = gen.generate_answer(q_id, {})
    answer_id = answer_result["answer_id"]
    edited = gen.edit_answer(answer_id, "My edited answer", diff_summary="Changed tone")
    assert edited["edited_answer"] == "My edited answer"
    assert edited["diff_summary"] == "Changed tone"
    assert "original_answer" in edited


def test_edit_answer_not_found(test_session):
    gen = _make_generator(test_session)
    with pytest.raises(ValueError, match="Answer not found"):
        gen.edit_answer("doesnotexist", "text")
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
source .venv/bin/activate && pytest backend/tests/unit/test_question_generator.py -v 2>&1 | head -20
```
Expected: ImportError.

- [ ] **Step 3: Create prompt YAML files**

```yaml
# backend/prompts/questions/generate.yaml
version: "1.0"
system: |
  You are a career coach. Generate interview questions based on the job description provided.
  Return a JSON array only — no explanation, no markdown fences, no preamble.
  Each object must have exactly two keys: question_template (string) and category (string).
  category must be one of: behavioral, technical, situational, motivational, cultural, role_specific.
  Use {{company}}, {{position}}, {{industry}}, {{tech_stack}} as placeholder variables where contextually relevant.
  Ground every question in the provided job description. Never invent requirements not present in the JD.
user_template: |
  Job Description:
  {job_description}

  Company: {company}
  Position: {position}
  Industry: {industry}
  Tech Stack: {tech_stack}

  Generate 5-8 interview questions as a JSON array.
```

```yaml
# backend/prompts/questions/answer.yaml
version: "1.0"
system: |
  You are a career coach writing job application answers.
  Answer ONLY from the evidence provided. Never invent employers, metrics, projects, or certifications.
  Return JSON only — no explanation, no markdown fences.
  JSON must have exactly two keys: answer_text (string) and confidence_level (string).
  confidence_level must be exactly one of: verified, strong_inference, weak_inference.
  verified = every claim directly supported by evidence.
  strong_inference = claims supported by multiple evidence items.
  weak_inference = any claim not directly evidenced.
user_template: |
  Question: {question}

  Evidence from career history:
  {evidence}

  Write a {length_target} answer grounded only in the evidence above.
```

- [ ] **Step 4: Create the `__init__.py` for the questions service**

Create `backend/services/questions/__init__.py` as an empty file.

- [ ] **Step 5: Implement QuestionGenerator**

```python
# backend/services/questions/generator.py
from __future__ import annotations

import json
import logging
import re
from typing import Any

from sqlalchemy.orm import Session

from backend.repositories.question import AnswerRepository, QuestionRepository

logger = logging.getLogger(__name__)

_VALID_LENGTHS = {"short", "medium", "long"}
_VALID_CONFIDENCE = {"verified", "strong_inference", "weak_inference"}
_VARIABLE_PATTERN = re.compile(r"\{\{(\w+)\}\}")

_FALLBACK_QUESTIONS = [
    {
        "question_template": "Tell me about your experience relevant to {{position}}.",
        "category": "behavioral",
    },
    {
        "question_template": "Why are you interested in the {{position}} role at {{company}}?",
        "category": "motivational",
    },
    {
        "question_template": "Describe a challenging situation in {{industry}} and how you handled it.",
        "category": "situational",
    },
    {
        "question_template": "What experience do you have with {{tech_stack}}?",
        "category": "technical",
    },
    {
        "question_template": "Where do you see yourself growing in the {{industry}} space?",
        "category": "motivational",
    },
]


def _interpolate(template: str, variables: dict[str, str]) -> str:
    """Replace {{var}} placeholders with values from variables dict."""
    def replace(m: re.Match) -> str:
        return variables.get(m.group(1), m.group(0))

    return _VARIABLE_PATTERN.sub(replace, template)


class QuestionGenerator:
    def __init__(
        self,
        ollama_client: Any,  # duck-typed OllamaClient
        prompt_loader: Any,  # duck-typed PromptLoader
        evidence_selector: Any,  # duck-typed EvidenceSelector
        session: Session,
    ) -> None:
        self._ollama = ollama_client
        self._loader = prompt_loader
        self._selector = evidence_selector
        self._session = session

    def generate_questions(
        self,
        job_description: str,
        company: str = "",
        position: str = "",
        industry: str = "",
        tech_stack: str = "",
        application_id: str | None = None,
    ) -> list[dict]:
        variables = {
            "company": company,
            "position": position,
            "industry": industry,
            "tech_stack": tech_stack,
        }
        raw = self._llm_generate_questions(job_description, variables)
        q_repo = QuestionRepository(self._session)
        results = []
        for item in raw:
            template = item.get("question_template", "")
            category = item.get("category", "behavioral")
            if category not in {
                "behavioral", "technical", "situational",
                "motivational", "cultural", "role_specific",
            }:
                category = "behavioral"
            detected_vars = _VARIABLE_PATTERN.findall(template)
            q = q_repo.create(
                question_template=template,
                category=category,
                length_target="medium",
                variables=detected_vars,
                source="generated",
                industry=industry or None,
            )
            results.append(
                {
                    "id": q.id,
                    "question_template": q.question_template,
                    "interpolated": _interpolate(q.question_template, variables),
                    "category": q.category,
                    "variables": q.variables,
                }
            )
        return results

    def generate_answer(
        self,
        question_id: str,
        variables: dict[str, str],
        application_id: str | None = None,
        length_target: str = "medium",
    ) -> dict:
        if length_target not in _VALID_LENGTHS:
            raise ValueError(f"Invalid length_target '{length_target}'")
        q_repo = QuestionRepository(self._session)
        a_repo = AnswerRepository(self._session)
        question = q_repo.get(question_id)
        if question is None:
            raise ValueError(f"Question not found: {question_id}")
        interpolated = _interpolate(question.question_template, variables)
        evidence = self._selector.select(interpolated, {}, max_bullets=6)
        answer_text, evidence_ids, confidence = self._llm_generate_answer(
            interpolated, evidence, length_target
        )
        answer = a_repo.create(
            question_id=question_id,
            application_id=application_id,
            original_answer=answer_text,
            confidence_level=confidence,
            evidence_ids=evidence_ids,
        )
        return {
            "answer_id": answer.id,
            "question_id": question_id,
            "interpolated_question": interpolated,
            "original_answer": answer.original_answer,
            "evidence_ids": answer.evidence_ids,
            "confidence_level": answer.confidence_level,
            "requires_approval": confidence == "weak_inference",
        }

    def edit_answer(
        self, answer_id: str, edited_text: str, diff_summary: str | None = None
    ) -> dict:
        a_repo = AnswerRepository(self._session)
        answer = a_repo.get(answer_id)
        if answer is None:
            raise ValueError(f"Answer not found: {answer_id}")
        answer.edited_answer = edited_text
        answer.diff_summary = diff_summary
        self._session.flush()
        self._session.refresh(answer)
        return {
            "answer_id": answer.id,
            "original_answer": answer.original_answer,
            "edited_answer": answer.edited_answer,
            "diff_summary": answer.diff_summary,
        }

    def _llm_generate_questions(
        self, job_description: str, variables: dict[str, str]
    ) -> list[dict]:
        if not self._ollama or not self._ollama.is_available():
            return _FALLBACK_QUESTIONS
        try:
            prompt_data = self._loader.load("questions/generate")
            user_prompt = prompt_data["user_template"].format(
                job_description=job_description,
                company=variables.get("company", ""),
                position=variables.get("position", ""),
                industry=variables.get("industry", ""),
                tech_stack=variables.get("tech_stack", ""),
            )
            raw = self._ollama.generate(
                model="qwen3:8b",
                prompt=user_prompt,
                system=prompt_data["system"],
                temperature=0.4,
            )
            match = re.search(r"\[.*\]", raw, re.DOTALL)
            if match:
                items = json.loads(match.group())
                if isinstance(items, list) and items:
                    return items
        except Exception:
            logger.exception("LLM question generation failed; using fallback")
        return _FALLBACK_QUESTIONS

    def _llm_generate_answer(
        self,
        question: str,
        evidence: list[dict],
        length_target: str,
    ) -> tuple[str, list[str], str]:
        evidence_ids = [
            e.get("evidence_id", "") for e in evidence if e.get("evidence_id")
        ]
        if not evidence:
            return (
                "Based on my professional background, I have relevant experience to address this question.",
                [],
                "weak_inference",
            )
        confidences = [e.get("confidence", "strong_inference") for e in evidence]
        if all(c == "verified" for c in confidences):
            overall_confidence = "verified"
        elif any(c in ("verified", "strong_inference") for c in confidences):
            overall_confidence = "strong_inference"
        else:
            overall_confidence = "weak_inference"

        if not self._ollama or not self._ollama.is_available():
            return self._template_answer(evidence, length_target), evidence_ids, overall_confidence

        evidence_text = "\n".join(
            f"- [{e.get('confidence', 'strong_inference')}] {e.get('bullet_text', '')}"
            for e in evidence[:8]
        )
        try:
            prompt_data = self._loader.load("questions/answer")
            user_prompt = prompt_data["user_template"].format(
                question=question,
                evidence=evidence_text,
                length_target=length_target,
            )
            raw = self._ollama.generate(
                model="qwen3:8b",
                prompt=user_prompt,
                system=prompt_data["system"],
                temperature=0.3,
            )
            match = re.search(r"\{.*\}", raw, re.DOTALL)
            if match:
                parsed = json.loads(match.group())
                text = parsed.get("answer_text", "")
                conf = parsed.get("confidence_level", overall_confidence)
                if conf not in _VALID_CONFIDENCE:
                    conf = "weak_inference"
                if text:
                    return text, evidence_ids, conf
        except Exception:
            logger.exception("LLM answer generation failed; using template fallback")
        return self._template_answer(evidence, length_target), evidence_ids, overall_confidence

    def _template_answer(self, evidence: list[dict], length_target: str) -> str:
        bullets = [e.get("bullet_text", "") for e in evidence[:4] if e.get("bullet_text")]
        if not bullets:
            return "Based on my professional background, I have relevant experience in this area."
        if length_target == "short":
            return bullets[0]
        return "In my career, " + " Additionally, ".join(bullets[:3]) + "."
```

- [ ] **Step 6: Run tests to verify they pass**

```bash
source .venv/bin/activate && pytest backend/tests/unit/test_question_generator.py -v
```
Expected: all 12 tests PASS.

- [ ] **Step 7: Commit**

```bash
git add backend/services/questions/__init__.py backend/services/questions/generator.py \
        backend/prompts/questions/generate.yaml backend/prompts/questions/answer.yaml \
        backend/tests/unit/test_question_generator.py
git commit -m "feat: add QuestionGenerator with evidence-grounded Q&A and fallback template"
```

---

### Task 4: Question/Answer API Routes

**Files:**
- Create: `backend/api/v1/routes/questions.py`
- Create: `backend/tests/integration/test_question_routes.py`
- Modify: `backend/main.py` (add questions router)

**Interfaces:**
- Consumes:
  - `QuestionGenerator` from Task 3 (`.generate_questions(...)`, `.generate_answer(...)`, `.edit_answer(...)`)
  - `QuestionRepository`, `AnswerRepository` from Task 2
  - `EvidenceSelector` from `backend/services/resume/evidence_selector.py`
  - `RAGRetriever`, `Reranker`, `Embedder`, `ChromaManager`, `OllamaClient`, `PromptLoader` — all existing
- Produces: REST endpoints at `/api/v1/questions/*`

- [ ] **Step 1: Write failing integration tests**

```python
# backend/tests/integration/test_question_routes.py
from __future__ import annotations

from unittest.mock import MagicMock, patch


def test_generate_questions(client):
    resp = client.post(
        "/api/v1/questions/generate",
        json={"job_description": "Python engineer needed", "company": "Acme", "position": "Engineer"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "questions" in data
    assert isinstance(data["questions"], list)
    assert len(data["questions"]) > 0
    q = data["questions"][0]
    assert "id" in q
    assert "question_template" in q
    assert "interpolated" in q
    assert "category" in q


def test_generate_answer(client):
    # First generate a question
    gen_resp = client.post(
        "/api/v1/questions/generate",
        json={"job_description": "Python engineer", "company": "Acme", "position": "Dev"},
    )
    q_id = gen_resp.json()["questions"][0]["id"]

    resp = client.post(
        f"/api/v1/questions/{q_id}/answer",
        json={"variables": {"company": "Acme", "position": "Dev"}, "length_target": "short"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "answer_id" in data
    assert "original_answer" in data
    assert "confidence_level" in data
    assert data["confidence_level"] in ("verified", "strong_inference", "weak_inference")
    assert "requires_approval" in data


def test_generate_answer_invalid_length(client):
    gen_resp = client.post(
        "/api/v1/questions/generate",
        json={"job_description": "Dev role"},
    )
    q_id = gen_resp.json()["questions"][0]["id"]
    resp = client.post(f"/api/v1/questions/{q_id}/answer", json={"length_target": "huge"})
    assert resp.status_code == 422


def test_generate_answer_question_not_found(client):
    resp = client.post("/api/v1/questions/doesnotexist/answer", json={})
    assert resp.status_code == 404


def test_edit_answer(client):
    gen_resp = client.post(
        "/api/v1/questions/generate", json={"job_description": "Dev role"}
    )
    q_id = gen_resp.json()["questions"][0]["id"]
    ans_resp = client.post(f"/api/v1/questions/{q_id}/answer", json={})
    answer_id = ans_resp.json()["answer_id"]

    edit_resp = client.patch(
        f"/api/v1/questions/{q_id}/answers/{answer_id}",
        json={"edited_text": "My refined answer", "diff_summary": "Improved tone"},
    )
    assert edit_resp.status_code == 200
    assert edit_resp.json()["edited_answer"] == "My refined answer"


def test_edit_answer_not_found(client):
    resp = client.patch(
        "/api/v1/questions/q1/answers/doesnotexist",
        json={"edited_text": "text"},
    )
    assert resp.status_code == 404


def test_list_questions_empty(client):
    resp = client.get("/api/v1/questions")
    assert resp.status_code == 200
    assert resp.json() == []


def test_list_questions_after_generation(client):
    client.post("/api/v1/questions/generate", json={"job_description": "Dev role"})
    resp = client.get("/api/v1/questions")
    assert resp.status_code == 200
    assert len(resp.json()) > 0


def test_list_questions_filter_by_category(client):
    client.post("/api/v1/questions/generate", json={"job_description": "Dev role"})
    resp = client.get("/api/v1/questions?category=behavioral")
    assert resp.status_code == 200
    for q in resp.json():
        assert q["category"] == "behavioral"


def test_list_answers_for_question(client):
    gen_resp = client.post(
        "/api/v1/questions/generate", json={"job_description": "Dev role"}
    )
    q_id = gen_resp.json()["questions"][0]["id"]
    client.post(f"/api/v1/questions/{q_id}/answer", json={})
    resp = client.get(f"/api/v1/questions/{q_id}/answers")
    assert resp.status_code == 200
    assert len(resp.json()) == 1


def test_list_answers_question_not_found(client):
    resp = client.get("/api/v1/questions/doesnotexist/answers")
    assert resp.status_code == 404
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
source .venv/bin/activate && pytest backend/tests/integration/test_question_routes.py -v 2>&1 | head -20
```
Expected: ImportError or 404s.

- [ ] **Step 3: Implement the questions API route**

```python
# backend/api/v1/routes/questions.py
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.config import Settings, get_settings
from backend.database import get_session
from backend.rag.chroma_client import ChromaManager
from backend.rag.embedder import Embedder
from backend.rag.retriever import RAGRetriever
from backend.rag.reranker import Reranker
from backend.repositories.question import AnswerRepository, QuestionRepository
from backend.services.ollama_client import OllamaClient
from backend.services.prompt_loader import PromptLoader
from backend.services.questions.generator import QuestionGenerator
from backend.services.resume.evidence_selector import EvidenceSelector

router = APIRouter(tags=["questions"])

_VALID_LENGTHS = {"short", "medium", "long"}


class GenerateQuestionsRequest(BaseModel):
    job_description: str
    company: str = ""
    position: str = ""
    industry: str = ""
    tech_stack: str = ""
    application_id: str | None = None


class GenerateAnswerRequest(BaseModel):
    variables: dict[str, str] = {}
    application_id: str | None = None
    length_target: str = "medium"


class EditAnswerRequest(BaseModel):
    edited_text: str
    diff_summary: str | None = None


def _build_generator(settings: Settings, session: Session) -> QuestionGenerator:
    ollama = OllamaClient(base_url=settings.ollama_base_url)
    embedder = Embedder(ollama, model=settings.embedding_model)
    chroma = ChromaManager(path=settings.chroma_db_path)
    retriever = RAGRetriever(chroma, embedder)
    reranker = Reranker()
    loader = PromptLoader()
    selector = EvidenceSelector(retriever, reranker)
    return QuestionGenerator(ollama, loader, selector, session)


@router.post("/questions/generate")
def generate_questions(
    body: GenerateQuestionsRequest, session: Session = Depends(get_session)
) -> dict:
    gen = _build_generator(get_settings(), session)
    return {
        "questions": gen.generate_questions(
            body.job_description,
            company=body.company,
            position=body.position,
            industry=body.industry,
            tech_stack=body.tech_stack,
            application_id=body.application_id,
        )
    }


@router.post("/questions/{question_id}/answer")
def generate_answer(
    question_id: str,
    body: GenerateAnswerRequest,
    session: Session = Depends(get_session),
) -> dict:
    if body.length_target not in _VALID_LENGTHS:
        raise HTTPException(
            status_code=422, detail=f"Invalid length_target '{body.length_target}'"
        )
    gen = _build_generator(get_settings(), session)
    try:
        return gen.generate_answer(
            question_id=question_id,
            variables=body.variables,
            application_id=body.application_id,
            length_target=body.length_target,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.patch("/questions/{question_id}/answers/{answer_id}")
def edit_answer(
    question_id: str,
    answer_id: str,
    body: EditAnswerRequest,
    session: Session = Depends(get_session),
) -> dict:
    gen = _build_generator(get_settings(), session)
    try:
        return gen.edit_answer(
            answer_id=answer_id,
            edited_text=body.edited_text,
            diff_summary=body.diff_summary,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.get("/questions")
def list_questions(
    category: str | None = None, session: Session = Depends(get_session)
) -> list[dict]:
    q_repo = QuestionRepository(session)
    questions = q_repo.get_by_category(category) if category else q_repo.list()
    return [
        {
            "id": q.id,
            "question_template": q.question_template,
            "category": q.category,
            "variables": q.variables,
        }
        for q in questions
    ]


@router.get("/questions/{question_id}/answers")
def list_answers(
    question_id: str, session: Session = Depends(get_session)
) -> list[dict]:
    q_repo = QuestionRepository(session)
    if q_repo.get(question_id) is None:
        raise HTTPException(status_code=404, detail="Question not found")
    a_repo = AnswerRepository(session)
    answers = a_repo.get_by_question(question_id)
    return [
        {
            "id": a.id,
            "original_answer": a.original_answer,
            "edited_answer": a.edited_answer,
            "confidence_level": a.confidence_level,
            "evidence_ids": a.evidence_ids,
            "created_at": a.created_at,
        }
        for a in answers
    ]
```

- [ ] **Step 4: Register the router in main.py**

In `backend/main.py`, add:

```python
# import (with other route imports):
from backend.api.v1.routes.questions import router as questions_router

# in create_app() (with other include_router calls):
app.include_router(questions_router, prefix="/api/v1")
```

- [ ] **Step 5: Run the tests and verify they pass**

```bash
source .venv/bin/activate && pytest backend/tests/integration/test_question_routes.py -v
```
Expected: all 11 tests PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/api/v1/routes/questions.py backend/tests/integration/test_question_routes.py backend/main.py
git commit -m "feat: add Q&A API routes for question generation, answer generation, and editing"
```

---

### Task 5: Learning Engine — Outcome Ranker

**Files:**
- Create: `backend/services/learning/__init__.py`
- Create: `backend/services/learning/ranker.py`
- Create: `backend/tests/unit/test_outcome_ranker.py`

**Interfaces:**
- Consumes: `OutcomeSignalRepository` from Task 2 (`.list()`, `.create(**kwargs)`)
- Produces:
  - `OutcomeRanker(session: Session)`
  - `.record_outcome(application_id, signal_type, resume_id, template_used, ats_score, industry, position_type) -> dict`
    - Returns `{signal_id, signal_type, signal_weight, application_id}`
    - Raises `ValueError("Invalid signal_type '...'")` for unknown signal types
  - `.get_template_rankings() -> list[dict]`
    - Returns `[{template_name, score, signal_count, signal_types}]` sorted descending by score
  - `.get_ats_vs_outcome_correlation() -> dict`
    - Returns `{buckets: [{range, outcome_rate, count}], total_signals: int}`
  - Signal weights (constants): `no_response=0.0`, `rejected=0.1`, `phone_screen=0.4`, `interview=0.7`, `final_round=0.85`, `offer=1.0`, `accepted=1.0`

- [ ] **Step 1: Write failing unit tests**

```python
# backend/tests/unit/test_outcome_ranker.py
from __future__ import annotations

import pytest
from backend.repositories.application import ApplicationRepository
from backend.services.learning.ranker import OutcomeRanker


def _make_app(session, company="Acme", position="Engineer"):
    return ApplicationRepository(session).create(company=company, position=position)


def test_record_outcome_valid_signal(test_session):
    app = _make_app(test_session)
    ranker = OutcomeRanker(test_session)
    result = ranker.record_outcome(
        application_id=app.id, signal_type="interview", template_used="software"
    )
    assert result["signal_type"] == "interview"
    assert result["signal_weight"] == 0.7
    assert result["application_id"] == app.id
    assert "signal_id" in result


def test_record_outcome_all_weight_values(test_session):
    expected = {
        "no_response": 0.0, "rejected": 0.1, "phone_screen": 0.4,
        "interview": 0.7, "final_round": 0.85, "offer": 1.0, "accepted": 1.0,
    }
    ranker = OutcomeRanker(test_session)
    for signal_type, weight in expected.items():
        app = _make_app(test_session, company=signal_type, position="P")
        result = ranker.record_outcome(application_id=app.id, signal_type=signal_type)
        assert result["signal_weight"] == weight, f"Wrong weight for {signal_type}"


def test_record_outcome_invalid_signal_type(test_session):
    app = _make_app(test_session)
    ranker = OutcomeRanker(test_session)
    with pytest.raises(ValueError, match="Invalid signal_type"):
        ranker.record_outcome(application_id=app.id, signal_type="hired")


def test_get_template_rankings_empty(test_session):
    ranker = OutcomeRanker(test_session)
    assert ranker.get_template_rankings() == []


def test_get_template_rankings_sorted_descending(test_session):
    ranker = OutcomeRanker(test_session)
    app1 = _make_app(test_session, company="A")
    app2 = _make_app(test_session, company="B")
    ranker.record_outcome(app1.id, "offer", template_used="software")
    ranker.record_outcome(app2.id, "rejected", template_used="ai")
    rankings = ranker.get_template_rankings()
    assert len(rankings) == 2
    assert rankings[0]["template_name"] == "software"
    assert rankings[0]["score"] == 1.0
    assert rankings[1]["template_name"] == "ai"
    assert rankings[1]["score"] == 0.1


def test_get_template_rankings_averages_multiple_signals(test_session):
    ranker = OutcomeRanker(test_session)
    app1 = _make_app(test_session, company="A")
    app2 = _make_app(test_session, company="B")
    ranker.record_outcome(app1.id, "offer", template_used="software")   # weight 1.0
    ranker.record_outcome(app2.id, "rejected", template_used="software")  # weight 0.1
    rankings = ranker.get_template_rankings()
    assert rankings[0]["score"] == pytest.approx(0.55, abs=1e-3)
    assert rankings[0]["signal_count"] == 2


def test_get_template_rankings_includes_signal_types(test_session):
    ranker = OutcomeRanker(test_session)
    app = _make_app(test_session)
    ranker.record_outcome(app.id, "interview", template_used="consulting")
    rankings = ranker.get_template_rankings()
    assert "interview" in rankings[0]["signal_types"]


def test_ats_vs_outcome_no_data(test_session):
    ranker = OutcomeRanker(test_session)
    result = ranker.get_ats_vs_outcome_correlation()
    assert result["total_signals"] == 0
    assert all(b["count"] == 0 for b in result["buckets"])


def test_ats_vs_outcome_correct_bucket_assignment(test_session):
    ranker = OutcomeRanker(test_session)
    app1 = _make_app(test_session, company="A")
    app2 = _make_app(test_session, company="B")
    app3 = _make_app(test_session, company="C")
    ranker.record_outcome(app1.id, "offer", ats_score=85.0)   # 80-100 bucket
    ranker.record_outcome(app2.id, "rejected", ats_score=30.0)  # 20-40 bucket
    ranker.record_outcome(app3.id, "interview", ats_score=55.0)  # 40-60 bucket
    result = ranker.get_ats_vs_outcome_correlation()
    assert result["total_signals"] == 3
    bucket_map = {b["range"]: b for b in result["buckets"]}
    assert bucket_map["80-100"]["count"] == 1
    assert bucket_map["80-100"]["outcome_rate"] == 1.0
    assert bucket_map["20-40"]["count"] == 1
    assert bucket_map["20-40"]["outcome_rate"] == pytest.approx(0.1)
    assert bucket_map["0-20"]["count"] == 0
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
source .venv/bin/activate && pytest backend/tests/unit/test_outcome_ranker.py -v 2>&1 | head -20
```
Expected: ImportError.

- [ ] **Step 3: Create `__init__.py` for the learning service**

Create `backend/services/learning/__init__.py` as an empty file.

- [ ] **Step 4: Implement OutcomeRanker**

```python
# backend/services/learning/ranker.py
from __future__ import annotations

import logging
from collections import defaultdict

from sqlalchemy.orm import Session

from backend.repositories.outcome import OutcomeSignalRepository

logger = logging.getLogger(__name__)

_SIGNAL_WEIGHTS: dict[str, float] = {
    "no_response": 0.0,
    "rejected": 0.1,
    "phone_screen": 0.4,
    "interview": 0.7,
    "final_round": 0.85,
    "offer": 1.0,
    "accepted": 1.0,
}

_VALID_SIGNALS = set(_SIGNAL_WEIGHTS.keys())


class OutcomeRanker:
    def __init__(self, session: Session) -> None:
        self._session = session

    def record_outcome(
        self,
        application_id: str,
        signal_type: str,
        resume_id: str | None = None,
        template_used: str | None = None,
        ats_score: float | None = None,
        industry: str | None = None,
        position_type: str | None = None,
    ) -> dict:
        if signal_type not in _VALID_SIGNALS:
            raise ValueError(
                f"Invalid signal_type '{signal_type}'. Must be one of {sorted(_VALID_SIGNALS)}"
            )
        repo = OutcomeSignalRepository(self._session)
        weight = _SIGNAL_WEIGHTS[signal_type]
        signal = repo.create(
            application_id=application_id,
            signal_type=signal_type,
            signal_weight=weight,
            resume_id=resume_id,
            template_used=template_used,
            ats_score=ats_score,
            industry=industry,
            position_type=position_type,
        )
        return {
            "signal_id": signal.id,
            "signal_type": signal.signal_type,
            "signal_weight": signal.signal_weight,
            "application_id": signal.application_id,
        }

    def get_template_rankings(self) -> list[dict]:
        repo = OutcomeSignalRepository(self._session)
        signals = repo.list()
        by_template: dict[str, list[float]] = defaultdict(list)
        signal_types_map: dict[str, list[str]] = defaultdict(list)
        for s in signals:
            key = s.template_used or "unknown"
            by_template[key].append(s.signal_weight)
            signal_types_map[key].append(s.signal_type)
        rankings = [
            {
                "template_name": template,
                "score": round(sum(weights) / len(weights), 4),
                "signal_count": len(weights),
                "signal_types": list(set(signal_types_map[template])),
            }
            for template, weights in by_template.items()
        ]
        rankings.sort(key=lambda r: r["score"], reverse=True)
        return rankings

    def get_ats_vs_outcome_correlation(self) -> dict:
        repo = OutcomeSignalRepository(self._session)
        signals = [s for s in repo.list() if s.ats_score is not None]
        buckets: dict[str, list[float]] = {
            "0-20": [], "20-40": [], "40-60": [], "60-80": [], "80-100": [],
        }
        for s in signals:
            score = s.ats_score
            if score < 20:
                buckets["0-20"].append(s.signal_weight)
            elif score < 40:
                buckets["20-40"].append(s.signal_weight)
            elif score < 60:
                buckets["40-60"].append(s.signal_weight)
            elif score < 80:
                buckets["60-80"].append(s.signal_weight)
            else:
                buckets["80-100"].append(s.signal_weight)
        result = [
            {
                "range": range_label,
                "outcome_rate": (
                    round(sum(weights) / len(weights), 4) if weights else 0.0
                ),
                "count": len(weights),
            }
            for range_label, weights in buckets.items()
        ]
        return {"buckets": result, "total_signals": len(signals)}
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
source .venv/bin/activate && pytest backend/tests/unit/test_outcome_ranker.py -v
```
Expected: all 9 tests PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/services/learning/__init__.py backend/services/learning/ranker.py \
        backend/tests/unit/test_outcome_ranker.py
git commit -m "feat: add OutcomeRanker with template rankings and ATS vs outcome correlation"
```

---

### Task 6: Learning Engine API

**Files:**
- Create: `backend/api/v1/routes/learning.py`
- Create: `backend/tests/integration/test_learning_routes.py`
- Modify: `backend/main.py` (add learning router)

**Interfaces:**
- Consumes: `OutcomeRanker` from Task 5
- Produces: REST endpoints at `/api/v1/learning/*`

- [ ] **Step 1: Write failing integration tests**

```python
# backend/tests/integration/test_learning_routes.py
from __future__ import annotations


def _make_app(client, company="Acme", position="Engineer"):
    resp = client.post("/api/v1/applications", json={"company": company, "position": position})
    return resp.json()["id"]


def test_record_outcome(client):
    app_id = _make_app(client)
    resp = client.post(
        "/api/v1/learning/outcome",
        json={"application_id": app_id, "signal_type": "interview", "template_used": "software"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["signal_type"] == "interview"
    assert data["signal_weight"] == 0.7
    assert "signal_id" in data


def test_record_outcome_invalid_signal(client):
    app_id = _make_app(client)
    resp = client.post(
        "/api/v1/learning/outcome",
        json={"application_id": app_id, "signal_type": "hired"},
    )
    assert resp.status_code == 422


def test_get_rankings_empty(client):
    resp = client.get("/api/v1/learning/rankings")
    assert resp.status_code == 200
    assert resp.json() == {"template_rankings": []}


def test_get_rankings_with_data(client):
    app_id = _make_app(client)
    client.post(
        "/api/v1/learning/outcome",
        json={"application_id": app_id, "signal_type": "offer", "template_used": "software"},
    )
    resp = client.get("/api/v1/learning/rankings")
    assert resp.status_code == 200
    rankings = resp.json()["template_rankings"]
    assert len(rankings) == 1
    assert rankings[0]["template_name"] == "software"
    assert rankings[0]["score"] == 1.0


def test_get_report(client):
    resp = client.get("/api/v1/learning/report")
    assert resp.status_code == 200
    data = resp.json()
    assert "template_rankings" in data
    assert "ats_vs_outcome" in data
    assert "buckets" in data["ats_vs_outcome"]
    assert "total_signals" in data["ats_vs_outcome"]


def test_get_report_with_ats_data(client):
    app_id = _make_app(client)
    client.post(
        "/api/v1/learning/outcome",
        json={
            "application_id": app_id,
            "signal_type": "offer",
            "ats_score": 90.0,
            "template_used": "software",
        },
    )
    resp = client.get("/api/v1/learning/report")
    assert resp.status_code == 200
    report = resp.json()
    assert report["ats_vs_outcome"]["total_signals"] == 1
    bucket_80 = next(
        b for b in report["ats_vs_outcome"]["buckets"] if b["range"] == "80-100"
    )
    assert bucket_80["count"] == 1
    assert bucket_80["outcome_rate"] == 1.0
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
source .venv/bin/activate && pytest backend/tests/integration/test_learning_routes.py -v 2>&1 | head -20
```
Expected: ImportError or 404s.

- [ ] **Step 3: Implement the learning API route**

```python
# backend/api/v1/routes/learning.py
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.database import get_session
from backend.services.learning.ranker import OutcomeRanker

router = APIRouter(tags=["learning"])

_VALID_SIGNALS = {
    "no_response", "rejected", "phone_screen", "interview",
    "final_round", "offer", "accepted",
}


class RecordOutcomeRequest(BaseModel):
    application_id: str
    signal_type: str
    resume_id: str | None = None
    template_used: str | None = None
    ats_score: float | None = None
    industry: str | None = None
    position_type: str | None = None


@router.post("/learning/outcome")
def record_outcome(
    body: RecordOutcomeRequest, session: Session = Depends(get_session)
) -> dict:
    if body.signal_type not in _VALID_SIGNALS:
        raise HTTPException(
            status_code=422, detail=f"Invalid signal_type '{body.signal_type}'"
        )
    ranker = OutcomeRanker(session)
    try:
        return ranker.record_outcome(
            application_id=body.application_id,
            signal_type=body.signal_type,
            resume_id=body.resume_id,
            template_used=body.template_used,
            ats_score=body.ats_score,
            industry=body.industry,
            position_type=body.position_type,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@router.get("/learning/rankings")
def get_rankings(session: Session = Depends(get_session)) -> dict:
    ranker = OutcomeRanker(session)
    return {"template_rankings": ranker.get_template_rankings()}


@router.get("/learning/report")
def get_effectiveness_report(session: Session = Depends(get_session)) -> dict:
    ranker = OutcomeRanker(session)
    return {
        "template_rankings": ranker.get_template_rankings(),
        "ats_vs_outcome": ranker.get_ats_vs_outcome_correlation(),
    }
```

- [ ] **Step 4: Register the router in main.py**

In `backend/main.py`, add:

```python
# import (with other route imports):
from backend.api.v1.routes.learning import router as learning_router

# in create_app() (with other include_router calls):
app.include_router(learning_router, prefix="/api/v1")
```

- [ ] **Step 5: Run the tests and verify they pass**

```bash
source .venv/bin/activate && pytest backend/tests/integration/test_learning_routes.py -v
```
Expected: all 7 tests PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/api/v1/routes/learning.py backend/tests/integration/test_learning_routes.py backend/main.py
git commit -m "feat: add Learning Engine API with outcome recording, template rankings, and ATS correlation"
```

---

### Task 7: Career Copilot Engine

**Files:**
- Create: `backend/services/copilot/__init__.py`
- Create: `backend/services/copilot/engine.py`
- Create: `backend/prompts/copilot/chat.yaml`
- Create: `backend/tests/unit/test_copilot_engine.py`

**Interfaces:**
- Consumes:
  - `RAGService` from `backend/services/rag/service.py`:
    - `.query(query: str, intent: str) -> dict` returning `{response, evidence, confidence_summary}`
    - `evidence` items: `{text, source, entity_id, confidence, similarity_score}`
  - Available intents (from `RAGService._INTENT_COLLECTIONS`): `resume_help`, `cover_letter_help`, `interview_prep`, `job_fit_analysis`, `career_advice`, `knowledge_lookup`
- Produces:
  - `CopilotEngine(rag_service: RAGService)`
  - `.chat(message: str, conversation_history: list[dict] | None) -> dict`
    - Returns `{response, intent, confidence, citations, evidence_count}`
    - `citations` is a list of `{source, text, confidence, similarity}` (up to 5)
    - `confidence` is the `confidence_summary` from RAGService (`"verified"`, `"strong_inference"`, `"weak_inference"`, or `"no_evidence"`)
  - `_detect_intent(message: str) -> str` — module-level function

- [ ] **Step 1: Write failing unit tests**

```python
# backend/tests/unit/test_copilot_engine.py
from __future__ import annotations

from unittest.mock import MagicMock

from backend.services.copilot.engine import CopilotEngine, _detect_intent


def _make_rag(
    response: str = "Test response",
    evidence: list | None = None,
    confidence: str = "strong_inference",
):
    rag = MagicMock()
    rag.query.return_value = {
        "response": response,
        "evidence": evidence or [],
        "confidence_summary": confidence,
    }
    return rag


def test_detect_intent_resume():
    assert _detect_intent("Help me improve my resume") == "resume_help"


def test_detect_intent_cover_letter():
    assert _detect_intent("Write me a cover letter for this role") == "cover_letter_help"


def test_detect_intent_interview():
    assert _detect_intent("How should I prepare for the interview?") == "interview_prep"


def test_detect_intent_job_fit():
    assert _detect_intent("Am I a good fit for this job?") == "job_fit_analysis"


def test_detect_intent_career_advice():
    assert _detect_intent("What career path should I take?") == "career_advice"


def test_detect_intent_default_fallback():
    assert _detect_intent("What is the meaning of life?") == "knowledge_lookup"


def test_chat_returns_all_required_keys():
    engine = CopilotEngine(_make_rag())
    result = engine.chat("Tell me about my background")
    assert set(result.keys()) >= {"response", "intent", "confidence", "citations", "evidence_count"}


def test_chat_response_matches_rag_output():
    engine = CopilotEngine(_make_rag(response="You have 5 years of experience."))
    result = engine.chat("What is my experience?")
    assert result["response"] == "You have 5 years of experience."


def test_chat_confidence_from_rag():
    engine = CopilotEngine(_make_rag(confidence="verified"))
    result = engine.chat("Tell me my skills")
    assert result["confidence"] == "verified"


def test_chat_evidence_becomes_citations():
    evidence = [
        {
            "source": "acos_experiences",
            "text": "Led a team of engineers at Acme Corp.",
            "confidence": "verified",
            "similarity_score": 0.95,
        },
        {
            "source": "acos_projects",
            "text": "Built a machine learning pipeline.",
            "confidence": "strong_inference",
            "similarity_score": 0.80,
        },
    ]
    engine = CopilotEngine(_make_rag(evidence=evidence))
    result = engine.chat("What are my achievements?")
    assert result["evidence_count"] == 2
    assert len(result["citations"]) == 2
    assert result["citations"][0]["source"] == "acos_experiences"
    assert result["citations"][0]["confidence"] == "verified"
    assert len(result["citations"][0]["text"]) <= 150


def test_chat_caps_citations_at_five():
    evidence = [
        {"source": f"acos_{i}", "text": f"Evidence {i}", "confidence": "verified", "similarity_score": 0.9}
        for i in range(10)
    ]
    engine = CopilotEngine(_make_rag(evidence=evidence))
    result = engine.chat("Query")
    assert len(result["citations"]) == 5
    assert result["evidence_count"] == 10


def test_chat_passes_history_context_to_rag():
    rag = _make_rag()
    engine = CopilotEngine(rag)
    history = [
        {"role": "user", "content": "Tell me about my Python skills"},
        {"role": "assistant", "content": "You have 5 years of Python experience."},
    ]
    engine.chat("Can you elaborate on that?", conversation_history=history)
    call_query = rag.query.call_args[0][0]
    assert "Can you elaborate on that?" in call_query


def test_chat_no_history_still_works():
    engine = CopilotEngine(_make_rag())
    result = engine.chat("Hello", conversation_history=[])
    assert result["response"] == "Test response"


def test_chat_none_history_defaults_to_empty():
    engine = CopilotEngine(_make_rag())
    result = engine.chat("Hello", conversation_history=None)
    assert result["response"] == "Test response"


def test_chat_intent_inferred_from_message():
    rag = _make_rag()
    engine = CopilotEngine(rag)
    engine.chat("Help me with my resume")
    _, kwargs = rag.query.call_args
    assert kwargs.get("intent") == "resume_help"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
source .venv/bin/activate && pytest backend/tests/unit/test_copilot_engine.py -v 2>&1 | head -20
```
Expected: ImportError.

- [ ] **Step 3: Create the copilot prompt**

```yaml
# backend/prompts/copilot/chat.yaml
version: "1.0"
system: |
  You are ACOS Career Copilot, an AI career assistant.
  Answer ONLY from the provided evidence. Never invent employers, metrics, dates, or certifications.
  Every factual claim must cite a specific piece of evidence.
  If the evidence does not support a claim, say so — do not fill gaps with assumptions.
  End every response with one line: "Confidence: [verified|strong_inference|weak_inference]"
user_template: |
  Conversation history:
  {history}

  Current question: {message}

  Evidence from career history:
  {evidence}
```

- [ ] **Step 4: Create `__init__.py` for the copilot service**

Create `backend/services/copilot/__init__.py` as an empty file.

- [ ] **Step 5: Implement CopilotEngine**

```python
# backend/services/copilot/engine.py
from __future__ import annotations

import logging

from backend.services.rag.service import RAGService

logger = logging.getLogger(__name__)

_INTENT_KEYWORDS: dict[str, list[str]] = {
    "resume_help": ["resume", "cv", "bullet", "template", "one-page", "tailor"],
    "cover_letter_help": ["cover letter", "cover_letter", "covering letter"],
    "interview_prep": ["interview", "behavioral", "technical", "whiteboard", "question", "prep"],
    "job_fit_analysis": ["fit", "match", "job", "jd", "requirement", "skill gap", "qualify"],
    "career_advice": ["career", "advice", "next step", "growth", "path", "pivot", "transition"],
}


def _detect_intent(message: str) -> str:
    lower = message.lower()
    for intent, keywords in _INTENT_KEYWORDS.items():
        if any(kw in lower for kw in keywords):
            return intent
    return "knowledge_lookup"


def _format_history(history: list[dict]) -> str:
    if not history:
        return ""
    lines = []
    for turn in history[-5:]:  # limit context to last 5 turns
        role = turn.get("role", "user").capitalize()
        content = turn.get("content", "")
        lines.append(f"{role}: {content}")
    return "\n".join(lines)


class CopilotEngine:
    def __init__(self, rag_service: RAGService) -> None:
        self._rag = rag_service

    def chat(
        self,
        message: str,
        conversation_history: list[dict] | None = None,
    ) -> dict:
        history = conversation_history or []
        intent = _detect_intent(message)
        history_text = _format_history(history)
        query = f"{history_text}\nUser: {message}".strip() if history_text else message
        rag_result = self._rag.query(query, intent=intent)
        evidence = rag_result.get("evidence", [])
        citations = [
            {
                "source": e["source"],
                "text": e["text"][:150],
                "confidence": e["confidence"],
                "similarity": e.get("similarity_score", 0.0),
            }
            for e in evidence[:5]
        ]
        return {
            "response": rag_result["response"],
            "intent": intent,
            "confidence": rag_result.get("confidence_summary", "no_evidence"),
            "citations": citations,
            "evidence_count": len(evidence),
        }
```

- [ ] **Step 6: Run tests to verify they pass**

```bash
source .venv/bin/activate && pytest backend/tests/unit/test_copilot_engine.py -v
```
Expected: all 14 tests PASS.

- [ ] **Step 7: Commit**

```bash
git add backend/services/copilot/__init__.py backend/services/copilot/engine.py \
        backend/prompts/copilot/chat.yaml \
        backend/tests/unit/test_copilot_engine.py
git commit -m "feat: add CopilotEngine with intent detection, multi-turn history, and evidence citations"
```

---

### Task 8: Copilot API + Register All Routers + Coverage Gate

**Files:**
- Create: `backend/api/v1/routes/copilot.py`
- Create: `backend/tests/integration/test_copilot_routes.py`
- Modify: `backend/main.py` (register copilot router; verify all 4 Phase 4 routers registered)

**Interfaces:**
- Consumes: `CopilotEngine` from Task 7; `RAGService` from Phase 2; existing infra stack.
- Produces: REST endpoints at `/api/v1/copilot/*`

- [ ] **Step 1: Write failing integration tests**

```python
# backend/tests/integration/test_copilot_routes.py
from __future__ import annotations

from unittest.mock import patch, MagicMock


def _mock_rag_result(response="Test answer", confidence="strong_inference"):
    return {
        "response": response,
        "evidence": [
            {
                "source": "acos_experiences",
                "text": "Led a team of 5 engineers at Acme Corp",
                "confidence": "verified",
                "similarity_score": 0.9,
            }
        ],
        "confidence_summary": confidence,
    }


def test_copilot_chat_basic(client):
    with patch("backend.api.v1.routes.copilot.RAGService") as MockRAG:
        MockRAG.return_value.query.return_value = _mock_rag_result()
        resp = client.post(
            "/api/v1/copilot/chat",
            json={"message": "Tell me about my background"},
        )
    assert resp.status_code == 200
    data = resp.json()
    assert "response" in data
    assert "intent" in data
    assert "confidence" in data
    assert "citations" in data
    assert "evidence_count" in data


def test_copilot_chat_with_history(client):
    with patch("backend.api.v1.routes.copilot.RAGService") as MockRAG:
        MockRAG.return_value.query.return_value = _mock_rag_result()
        resp = client.post(
            "/api/v1/copilot/chat",
            json={
                "message": "What did I do at Acme?",
                "conversation_history": [
                    {"role": "user", "content": "Tell me about my experience"},
                    {"role": "assistant", "content": "You worked at multiple companies."},
                ],
            },
        )
    assert resp.status_code == 200
    assert "response" in resp.json()


def test_copilot_chat_intent_inferred(client):
    with patch("backend.api.v1.routes.copilot.RAGService") as MockRAG:
        MockRAG.return_value.query.return_value = _mock_rag_result()
        resp = client.post(
            "/api/v1/copilot/chat",
            json={"message": "Help me fix my resume for this job"},
        )
    assert resp.status_code == 200
    assert resp.json()["intent"] == "resume_help"


def test_copilot_chat_interview_intent(client):
    with patch("backend.api.v1.routes.copilot.RAGService") as MockRAG:
        MockRAG.return_value.query.return_value = _mock_rag_result()
        resp = client.post(
            "/api/v1/copilot/chat",
            json={"message": "How should I prepare for my interview tomorrow?"},
        )
    assert resp.status_code == 200
    assert resp.json()["intent"] == "interview_prep"


def test_copilot_list_intents(client):
    resp = client.get("/api/v1/copilot/intents")
    assert resp.status_code == 200
    data = resp.json()
    assert "intents" in data
    intents = data["intents"]
    assert "resume_help" in intents
    assert "cover_letter_help" in intents
    assert "interview_prep" in intents
    assert "job_fit_analysis" in intents
    assert "career_advice" in intents
    assert "knowledge_lookup" in intents


def test_copilot_chat_citations_present(client):
    with patch("backend.api.v1.routes.copilot.RAGService") as MockRAG:
        MockRAG.return_value.query.return_value = _mock_rag_result()
        resp = client.post(
            "/api/v1/copilot/chat",
            json={"message": "What is my most recent job?"},
        )
    assert resp.status_code == 200
    citations = resp.json()["citations"]
    assert len(citations) == 1
    assert citations[0]["source"] == "acos_experiences"
    assert citations[0]["confidence"] == "verified"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
source .venv/bin/activate && pytest backend/tests/integration/test_copilot_routes.py -v 2>&1 | head -20
```
Expected: ImportError or 404s.

- [ ] **Step 3: Implement the copilot API route**

```python
# backend/api/v1/routes/copilot.py
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.config import get_settings
from backend.database import get_session
from backend.rag.chroma_client import ChromaManager
from backend.rag.embedder import Embedder
from backend.rag.retriever import RAGRetriever
from backend.rag.reranker import Reranker
from backend.services.copilot.engine import CopilotEngine
from backend.services.ollama_client import OllamaClient
from backend.services.rag.service import RAGService

router = APIRouter(tags=["copilot"])

_VALID_INTENTS = {
    "resume_help",
    "cover_letter_help",
    "interview_prep",
    "job_fit_analysis",
    "career_advice",
    "knowledge_lookup",
}


class ChatRequest(BaseModel):
    message: str
    conversation_history: list[dict] = []


def _build_copilot(session: Session) -> CopilotEngine:
    settings = get_settings()
    ollama = OllamaClient(base_url=settings.ollama_base_url)
    embedder = Embedder(ollama, model=settings.embedding_model)
    chroma = ChromaManager(path=settings.chroma_db_path)
    retriever = RAGRetriever(chroma, embedder)
    reranker = Reranker()
    rag_svc = RAGService(retriever, reranker, ollama if ollama.is_available() else None)
    return CopilotEngine(rag_svc)


@router.post("/copilot/chat")
def copilot_chat(
    body: ChatRequest, session: Session = Depends(get_session)
) -> dict:
    engine = _build_copilot(session)
    return engine.chat(body.message, conversation_history=body.conversation_history)


@router.get("/copilot/intents")
def list_intents() -> dict:
    return {"intents": sorted(_VALID_INTENTS)}
```

- [ ] **Step 4: Register the copilot router in main.py**

Final state of `backend/main.py` imports and router registrations:

```python
# All route imports (add the new line):
from backend.api.v1.routes.application import router as application_router
from backend.api.v1.routes.copilot import router as copilot_router
from backend.api.v1.routes.cover_letter import router as cover_letter_router
from backend.api.v1.routes.health import router as health_router
from backend.api.v1.routes.ingestion import router as ingestion_router
from backend.api.v1.routes.learning import router as learning_router
from backend.api.v1.routes.questions import router as questions_router
from backend.api.v1.routes.rag import router as rag_router
from backend.api.v1.routes.resume import router as resume_router

# All include_router calls in create_app():
app.include_router(health_router, prefix="/api/v1")
app.include_router(ingestion_router, prefix="/api/v1")
app.include_router(rag_router, prefix="/api/v1")
app.include_router(resume_router, prefix="/api/v1")
app.include_router(cover_letter_router, prefix="/api/v1")
app.include_router(application_router, prefix="/api/v1")
app.include_router(questions_router, prefix="/api/v1")
app.include_router(learning_router, prefix="/api/v1")
app.include_router(copilot_router, prefix="/api/v1")
```

- [ ] **Step 5: Run the copilot integration tests**

```bash
source .venv/bin/activate && pytest backend/tests/integration/test_copilot_routes.py -v
```
Expected: all 6 tests PASS.

- [ ] **Step 6: Run the full test suite**

```bash
source .venv/bin/activate && pytest backend/tests/ -v 2>&1 | tail -20
```
Expected: all existing + all new tests PASS, 0 failures.

- [ ] **Step 7: Run pyright type check**

```bash
source .venv/bin/activate && pyright backend/ 2>&1 | tail -10
```
Expected: 0 errors.

- [ ] **Step 8: Check coverage gate (≥90%)**

```bash
source .venv/bin/activate && pytest backend/tests/ \
    --cov=backend \
    --cov-report=term-missing \
    --cov-fail-under=90 \
    -q 2>&1 | tail -15
```
Expected: coverage ≥90%, gate PASSES. If coverage is below 90%, find uncovered lines with `--cov-report=term-missing` and add targeted tests until the gate passes.

- [ ] **Step 9: Commit**

```bash
git add backend/api/v1/routes/copilot.py backend/tests/integration/test_copilot_routes.py backend/main.py
git commit -m "feat: add Copilot chat API, register all Phase 4 routers, coverage gate ≥90%"
```

---

## Self-Review

### 1. Spec Coverage Check

| Requirement | Task |
|-------------|------|
| Career Copilot — conversational interface | Task 7 (`CopilotEngine.chat()` with `conversation_history`) |
| Career Copilot — evidence-based retrieval | Task 7 (delegates to `RAGService.query()`) |
| Career Copilot — multi-step reasoning | Task 7 (`_format_history` appends prior turns) |
| Career Copilot — confidence scoring | Task 7 (`confidence_summary` in response) |
| Career Copilot — sourcing from knowledge graph | Task 7 (RAGService queries ChromaDB collections) |
| Application CRM — full lifecycle | Task 1 (all 8 statuses, `transition_status`) |
| Application CRM — resume + cover letter linkage | Model already has `Resume.application_id`; CRM tracks the application; resume API accepts `application_id` (Phase 3) |
| Application CRM — outcome tracking | Task 6 (`POST /learning/outcome` links `application_id`) |
| Learning Engine — outcome-based ranking | Task 5 (`OutcomeRanker.get_template_rankings()`) |
| Learning Engine — interview success feedback | Task 6 (`record_outcome` with `interview`/`offer`/`final_round`) |
| Learning Engine — resume effectiveness tracking | Task 5 (`signal.template_used` + `signal.resume_id`) |
| Learning Engine — ATS vs outcome correlation | Task 5 (`get_ats_vs_outcome_correlation()`) |
| Q&A — job application question generator | Task 3 (`QuestionGenerator.generate_questions()`) |
| Q&A — variable system `{{company}}` etc. | Task 3 (`_interpolate()`, `_VARIABLE_PATTERN`) |
| Q&A — answer storage + editing | Task 3 (`generate_answer()`, `edit_answer()`) |
| Q&A — learning loop | Task 3 (`edit_answer()` stores `diff_summary` for future training) |
| System improves over time | Task 5 (`OutcomeRanker` accumulates signals; rankings update automatically) |
| No hallucinations | All services guard with `is_available()` + evidence-grounded fallback |
| Confidence scoring on all outputs | All routes return `confidence_level` / `requires_approval` |

### 2. Placeholder Scan

No TBDs. All steps contain actual code.

### 3. Type Consistency

- `_interpolate(template: str, variables: dict[str, str]) -> str` — used consistently in Task 3 + Task 4.
- `OutcomeRanker(session)` — session-only constructor, consistent in Tasks 5 and 6.
- `CopilotEngine(rag_service: RAGService)` — single constructor arg, consistent in Tasks 7 and 8.
- `QuestionGenerator(ollama, loader, selector, session)` — 4-arg constructor, consistent in Tasks 3 and 4.
- `AnswerRepository`, `QuestionRepository` — defined in Task 2, imported in Tasks 3 and 4.
- `OutcomeSignalRepository` — defined in Task 2, imported in Task 5.
