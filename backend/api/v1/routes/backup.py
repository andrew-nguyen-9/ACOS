from __future__ import annotations

from dataclasses import asdict
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from backend.config import get_settings
from backend.database import get_async_session
from backend.recovery import RECOVERY
from backend.services.backup.restore import RestoreError, restore
from backend.services.backup.snapshot import list_snapshots, snapshot

router = APIRouter(tags=["backup"])


class SnapshotRequest(BaseModel):
    full: bool = True


class RestoreRequest(BaseModel):
    snapshot_id: str


def _backups_dir() -> Path:
    # Backups live alongside the DB file (database/backups/), local-only.
    return Path(get_settings().db_path).parent / "backups"


@router.post("/backup/snapshot")
async def create_snapshot(
    body: SnapshotRequest, session: AsyncSession = Depends(get_async_session)
) -> dict:
    settings = get_settings()

    def _impl(s: Session):
        return snapshot(
            s, full=body.full, backups_dir=_backups_dir(),
            db_path=settings.db_path, chroma_path=settings.chroma_db_path,
            app_version=settings.app_version,
        )

    return asdict(await session.run_sync(_impl))


@router.get("/backup/list")
def list_backups() -> dict:
    return {"snapshots": [asdict(m) for m in list_snapshots(_backups_dir())]}


@router.post("/backup/restore")
def restore_snapshot(body: RestoreRequest) -> dict:
    from backend import database

    settings = get_settings()
    # Drop the live connection pools (sync + async) so no handle holds the DB file
    # open during the swap; reset_engine() rebuilds both against the restored file.
    database.engine.dispose()
    database.async_engine.sync_engine.dispose()
    try:
        result = restore(
            body.snapshot_id, backups_dir=_backups_dir(),
            db_path=settings.db_path, chroma_path=settings.chroma_db_path,
            app_version=settings.app_version,
        )
    except RestoreError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    finally:
        database.reset_engine()
    # A successful restore clears recovery mode (the corrupt DB has been replaced).
    if result.integrity_ok:
        RECOVERY.clear()
    return asdict(result)


@router.get("/recovery/status")
def recovery_status() -> dict:
    return {"readonly": RECOVERY.readonly, "reason": RECOVERY.reason}
