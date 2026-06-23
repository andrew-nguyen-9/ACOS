from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from backend.config import get_settings
from backend.database import get_async_session
from backend.services.observability.drift import DriftDetector, DriftSnapshot
from backend.services.observability.metrics import MetricsStore

router = APIRouter(prefix="/observability", tags=["observability"])


@router.get("/drift")
async def drift(session: AsyncSession = Depends(get_async_session)) -> dict:
    report = await session.run_sync(lambda s: DriftDetector(s).report())
    return {"metrics": report}


@router.post("/drift/snapshot")
async def drift_snapshot(session: AsyncSession = Depends(get_async_session)) -> dict:
    """Record a versioned drift sample from current data (off the hot path).

    Triggered on demand / by maintenance — mirrors POST /flywheel/evolution-loop;
    no new scheduler. Stamps the sample with the app version (14.1) so a drift is
    always measured against a known build.
    """
    app_version = get_settings().app_version
    return await session.run_sync(lambda s: DriftSnapshot(s).record(app_version))


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
