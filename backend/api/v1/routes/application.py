from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.database import get_session
from backend.observability import log_operation
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
    log_operation(
        "application_event",
        application_id=app.id,
        event="created",
        status=app.status,
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
    log_operation(
        "application_event",
        application_id=app.id,
        event="status_change",
        status=app.status,
    )
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


@router.delete("/applications/{application_id}")
def delete_application(
    application_id: str, session: Session = Depends(get_session)
) -> Response:
    repo = ApplicationRepository(session)
    if not repo.delete(application_id):
        raise HTTPException(status_code=404, detail="Application not found")
    return Response(status_code=204)
