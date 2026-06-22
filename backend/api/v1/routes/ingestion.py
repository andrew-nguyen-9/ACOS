from __future__ import annotations

import logging
import os
import shutil
import tempfile
import uuid
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, File, HTTPException, Request, UploadFile
from fastapi.responses import JSONResponse, StreamingResponse

from backend.api.v1.sse import sse_status_stream
from backend.ingestion import security
from backend.ingestion.jobs import JOBS, TERMINAL, IngestJob, run_ingest_job

logger = logging.getLogger(__name__)

router = APIRouter(tags=["ingestion"])

_ALLOWED_EXTENSIONS = {".txt", ".md", ".markdown", ".pdf", ".docx"}


@router.post("/ingest")
async def ingest_file(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
) -> JSONResponse:
    """Accept a file upload, validate it, and queue background ingestion.

    Returns 202 + a job id immediately. Security validation (extension, filename
    sanitisation, size limit) runs HERE on the request thread — never deferred to
    the background task where the error could not reach the client.
    """
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in _ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type {suffix!r}. Allowed: {sorted(_ALLOWED_EXTENSIONS)}",
        )

    # Persistent temp dir (survives until the background task cleans it up).
    tmpdir = tempfile.mkdtemp(prefix="acos_ingest_")
    safe_name = security.sanitize_filename(file.filename)
    dest = (Path(tmpdir) / safe_name).resolve()
    if not str(dest).startswith(str(Path(tmpdir).resolve()) + os.sep):
        shutil.rmtree(tmpdir, ignore_errors=True)
        raise HTTPException(status_code=400, detail="Invalid filename")
    with dest.open("wb") as f:
        shutil.copyfileobj(file.file, f)

    try:
        security.validate_size(dest)
    except ValueError as exc:
        shutil.rmtree(tmpdir, ignore_errors=True)
        raise HTTPException(status_code=422, detail=str(exc))

    job_id = uuid.uuid4().hex
    JOBS[job_id] = IngestJob(id=job_id, status="queued", filename=safe_name)
    background_tasks.add_task(run_ingest_job, job_id, str(dest), tmpdir)
    return JSONResponse(status_code=202, content={"job_id": job_id, "status": "queued"})


@router.get("/ingest/{job_id}")
async def ingest_status(job_id: str) -> dict:
    job = JOBS.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Unknown job id")
    return job.public()


@router.get("/ingest/{job_id}/stream")
async def ingest_progress(job_id: str, request: Request) -> StreamingResponse:
    if job_id not in JOBS:
        raise HTTPException(status_code=404, detail="Unknown job id")

    def _snapshot() -> dict | None:
        job = JOBS.get(job_id)
        return job.public() if job else None

    return StreamingResponse(
        sse_status_stream(request, _snapshot, TERMINAL),
        media_type="text/event-stream",
    )
