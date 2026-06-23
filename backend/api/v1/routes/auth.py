"""Phase 16.1 auth routes (ADR-014). Unauthenticated by design — these establish the
session that every tenant-scoped router then requires. Not behind the tenant
dependency (no tenant exists until login)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from backend.database import get_async_session
from backend.services import auth as auth_service

router = APIRouter(tags=["auth"], prefix="/auth")


class SecretBody(BaseModel):
    secret: str = Field(min_length=1)
    name: str | None = None


def _bearer(authorization: str | None) -> str | None:
    if authorization and authorization.lower().startswith("bearer "):
        return authorization[7:].strip() or None
    return None


@router.get("/status")
async def status(session: AsyncSession = Depends(get_async_session)) -> dict:
    enrolled = await session.run_sync(auth_service.is_enrolled)
    return {"enrolled": enrolled}


@router.post("/enroll")
async def enroll(body: SecretBody, session: AsyncSession = Depends(get_async_session)) -> dict:
    def _impl(s: Session) -> str:
        try:
            auth_service.enroll(s, body.secret, name=body.name)
        except auth_service.AuthError as exc:
            raise HTTPException(status_code=409, detail=str(exc))
        return auth_service.login(s, body.secret)

    token = await session.run_sync(_impl)
    return {"token": token}


@router.post("/login")
async def login(body: SecretBody, session: AsyncSession = Depends(get_async_session)) -> dict:
    def _impl(s: Session) -> str:
        try:
            return auth_service.login(s, body.secret)
        except auth_service.AuthError:
            # Uniform 401 — don't distinguish "not enrolled" from "wrong secret".
            raise HTTPException(status_code=401, detail="invalid credentials")

    token = await session.run_sync(_impl)
    return {"token": token}


@router.post("/logout")
async def logout(
    authorization: str | None = Header(default=None),
    session: AsyncSession = Depends(get_async_session),
) -> dict:
    token = _bearer(authorization)
    await session.run_sync(lambda s: auth_service.logout(s, token))
    return {"ok": True}
