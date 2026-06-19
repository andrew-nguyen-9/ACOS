from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient
from starlette.exceptions import HTTPException as StarletteHTTPException

from backend.api.errors import APIError, install_error_handlers


def _app() -> FastAPI:
    app = FastAPI()
    install_error_handlers(app)

    @app.get("/boom")
    def boom():
        raise APIError("NOT_FOUND", "thing missing", 404, {"id": "x"})

    @app.get("/starlette")
    def starlette():
        raise StarletteHTTPException(status_code=403, detail="nope")

    @app.get("/crash")
    def crash():
        raise RuntimeError("unexpected")

    @app.get("/validate")
    def validate(n: int):  # missing required query param -> RequestValidationError
        return {"n": n}

    return app


def test_apierror_envelope():
    c = TestClient(_app(), raise_server_exceptions=False)
    r = c.get("/boom")
    assert r.status_code == 404
    body = r.json()
    assert body == {"error": {"code": "NOT_FOUND", "message": "thing missing", "detail": {"id": "x"}}}


def test_validation_error_envelope():
    c = TestClient(_app(), raise_server_exceptions=False)
    r = c.get("/validate")
    assert r.status_code == 422
    body = r.json()
    assert body["error"]["code"] == "VALIDATION_ERROR"
    assert isinstance(body["error"]["detail"], (list, dict))


def test_starlette_http_exception_envelope():
    c = TestClient(_app(), raise_server_exceptions=False)
    r = c.get("/starlette")
    assert r.status_code == 403
    assert r.json()["error"]["code"] == "HTTP_403"


def test_unhandled_exception_envelope():
    c = TestClient(_app(), raise_server_exceptions=False)
    r = c.get("/crash")
    assert r.status_code == 500
    body = r.json()
    assert body["error"]["code"] == "INTERNAL"
    assert "message" in body["error"]
