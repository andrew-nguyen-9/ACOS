from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from backend.database import get_async_session
from backend.services.observability.drift import DriftDetector
from backend.services.observability.metrics import MetricsStore

router = APIRouter(prefix="/observability", tags=["observability"])


@router.get("/drift")
async def drift(session: AsyncSession = Depends(get_async_session)) -> dict:
    report = await session.run_sync(lambda s: DriftDetector(s).report())
    return {"metrics": report}


@router.get("/metrics")
async def metrics(
    kind: str = Query(...),
    session: AsyncSession = Depends(get_async_session),
) -> dict:
    def _impl(s: Session) -> dict:
        series = MetricsStore(s).series(kind)
        return {
            "kind": kind,
            "count": len(series),
            "series": [
                {"value": m.value, "meta": m.meta_json, "created_at": m.created_at}
                for m in series
            ],
        }

    return await session.run_sync(_impl)
