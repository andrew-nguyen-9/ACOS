from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from backend.database import get_session
from backend.services.observability.drift import DriftDetector
from backend.services.observability.metrics import MetricsStore

router = APIRouter(prefix="/observability", tags=["observability"])


@router.get("/drift")
def drift(session: Session = Depends(get_session)) -> dict:
    return {"metrics": DriftDetector(session).report()}


@router.get("/metrics")
def metrics(
    kind: str = Query(...),
    session: Session = Depends(get_session),
) -> dict:
    store = MetricsStore(session)
    series = store.series(kind)
    return {
        "kind": kind,
        "count": len(series),
        "series": [
            {"value": m.value, "meta": m.meta_json, "created_at": m.created_at}
            for m in series
        ],
    }
