from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.database import get_session
from backend.repositories.system_config import SystemConfigRepository

router = APIRouter(tags=["settings"])

_EDITABLE_KEYS = {
    "default_model",
    "embedding_model",
    "github_username",
    "learning_trigger_count",
    "ats_keyword_weight",
    "ats_skill_weight",
}


class UpdateSettingRequest(BaseModel):
    value: str


@router.get("/settings")
def get_settings(session: Session = Depends(get_session)) -> dict:
    repo = SystemConfigRepository(session)
    rows = repo.list()
    return {"settings": {r.key: r.value for r in rows if r.key != "onboarding_complete"}}


@router.put("/settings/{key}")
def update_setting(
    key: str, body: UpdateSettingRequest, session: Session = Depends(get_session)
) -> dict:
    if key not in _EDITABLE_KEYS:
        raise HTTPException(status_code=404, detail=f"Unknown setting key '{key}'")
    repo = SystemConfigRepository(session)
    record = repo.set_value(key, body.value)
    return {"key": record.key, "value": record.value}


@router.get("/settings/onboarding")
def onboarding_status(session: Session = Depends(get_session)) -> dict:
    repo = SystemConfigRepository(session)
    value = repo.get_value("onboarding_complete", default="false")
    return {"completed": value == "true"}


@router.post("/settings/onboarding/complete")
def complete_onboarding(session: Session = Depends(get_session)) -> dict:
    repo = SystemConfigRepository(session)
    repo.set_value("onboarding_complete", "true")
    return {"completed": True}
