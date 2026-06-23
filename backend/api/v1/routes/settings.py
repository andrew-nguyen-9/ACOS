from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from backend.database import get_async_session
from backend.repositories.system_config import SystemConfigRepository

router = APIRouter(tags=["settings"])

_EDITABLE_KEYS = {
    "default_model",
    "embedding_model",
    "github_username",
    "learning_trigger_count",
    "ats_keyword_weight",
    "ats_skill_weight",
    "ats_experience_weight",
    "ats_industry_weight",
    "ats_education_weight",
    "audit_policy",  # 16.3 (ADR-016): "enforced" | "relaxed"
}

_FLOAT_KEYS = {
    "ats_keyword_weight",
    "ats_skill_weight",
    "ats_experience_weight",
    "ats_industry_weight",
    "ats_education_weight",
}
_INT_KEYS = {"learning_trigger_count"}
_ENUM_KEYS = {"audit_policy": {"enforced", "relaxed"}}


def _validate_value(key: str, value: str) -> None:
    if key in _ENUM_KEYS:
        if value not in _ENUM_KEYS[key]:
            raise HTTPException(
                status_code=422,
                detail=f"{key} must be one of {sorted(_ENUM_KEYS[key])}",
            )
    elif key in _FLOAT_KEYS:
        try:
            v = float(value)
        except ValueError:
            raise HTTPException(status_code=422, detail=f"{key} must be a float")
        if not (0.0 <= v <= 1.0):
            raise HTTPException(status_code=422, detail=f"{key} must be between 0 and 1")
    elif key in _INT_KEYS:
        try:
            v = int(value)
        except ValueError:
            raise HTTPException(status_code=422, detail=f"{key} must be a positive integer")
        if v < 1:
            raise HTTPException(status_code=422, detail=f"{key} must be >= 1")


class UpdateSettingRequest(BaseModel):
    value: str


@router.get("/settings")
async def get_settings(session: AsyncSession = Depends(get_async_session)) -> dict:
    def _impl(s: Session) -> dict:
        rows = SystemConfigRepository(s).list()
        return {"settings": {r.key: r.value for r in rows if r.key != "onboarding_complete"}}

    return await session.run_sync(_impl)


@router.put("/settings/{key}")
async def update_setting(
    key: str, body: UpdateSettingRequest, session: AsyncSession = Depends(get_async_session)
) -> dict:
    if key not in _EDITABLE_KEYS:
        raise HTTPException(status_code=404, detail=f"Unknown setting key '{key}'")
    _validate_value(key, body.value)

    def _impl(s: Session) -> dict:
        record = SystemConfigRepository(s).set_value(key, body.value)
        return {"key": record.key, "value": record.value}

    return await session.run_sync(_impl)


@router.get("/settings/onboarding")
async def onboarding_status(session: AsyncSession = Depends(get_async_session)) -> dict:
    value = await session.run_sync(
        lambda s: SystemConfigRepository(s).get_value("onboarding_complete", default="false")
    )
    return {"completed": value == "true"}


@router.post("/settings/onboarding/complete")
async def complete_onboarding(session: AsyncSession = Depends(get_async_session)) -> dict:
    await session.run_sync(lambda s: SystemConfigRepository(s).set_value("onboarding_complete", "true"))
    return {"completed": True}
