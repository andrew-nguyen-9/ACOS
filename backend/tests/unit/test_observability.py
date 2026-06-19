from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.observability import TimingMiddleware, log_operation


def test_log_operation_emits_structured_line(caplog):
    with caplog.at_level(logging.INFO, logger="acos.op"):
        log_operation("resume_generate", resume_id="abc", bullets=4, confidence="strong_inference")
    msgs = [r.getMessage() for r in caplog.records if r.name == "acos.op"]
    assert any("op=resume_generate" in m and "resume_id=abc" in m and "bullets=4" in m for m in msgs)


def test_log_operation_emits_all_fields(caplog):
    with caplog.at_level(logging.INFO, logger="acos.op"):
        log_operation("ats_score", overall=85, intent="resume_help")
    msgs = [r.getMessage() for r in caplog.records if r.name == "acos.op"]
    assert any("op=ats_score" in m and "overall=85" in m and "intent=resume_help" in m for m in msgs)


def test_log_operation_no_extra_fields(caplog):
    with caplog.at_level(logging.INFO, logger="acos.op"):
        log_operation("simple_op")
    msgs = [r.getMessage() for r in caplog.records if r.name == "acos.op"]
    assert any("op=simple_op" in m for m in msgs)


def test_timing_middleware_sets_header_and_logs(caplog):
    app = FastAPI()
    app.add_middleware(TimingMiddleware)

    @app.get("/ping")
    def ping():
        return {"ok": True}

    c = TestClient(app)
    with caplog.at_level(logging.INFO, logger="acos.perf"):
        r = c.get("/ping")
    assert r.status_code == 200
    assert "X-Process-Time-Ms" in r.headers
    assert float(r.headers["X-Process-Time-Ms"]) >= 0.0
    perf = [rec.getMessage() for rec in caplog.records if rec.name == "acos.perf"]
    assert any("path=/ping" in m and "status=200" in m and "ms=" in m for m in perf)


def test_timing_middleware_header_format(caplog):
    """Header value must be a float formatted to 2 decimal places."""
    app = FastAPI()
    app.add_middleware(TimingMiddleware)

    @app.get("/check")
    def check():
        return {}

    c = TestClient(app)
    r = c.get("/check")
    header_val = r.headers["X-Process-Time-Ms"]
    # Must be parseable as float and have 2 decimal places
    assert "." in header_val
    parts = header_val.split(".")
    assert len(parts) == 2
    assert len(parts[1]) == 2


def test_timing_middleware_logs_method(caplog):
    """Log line must include the HTTP method."""
    app = FastAPI()
    app.add_middleware(TimingMiddleware)

    @app.get("/method-check")
    def method_check():
        return {}

    c = TestClient(app)
    with caplog.at_level(logging.INFO, logger="acos.perf"):
        c.get("/method-check")
    perf = [rec.getMessage() for rec in caplog.records if rec.name == "acos.perf"]
    assert any("method=GET" in m for m in perf)
