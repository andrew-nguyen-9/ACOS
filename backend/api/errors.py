from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger("acos.error")


class APIError(Exception):
    def __init__(self, code: str, message: str, status_code: int, detail: dict | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code
        self.detail = detail


def _envelope(code: str, message: str, detail: object | None) -> dict:
    return {"error": {"code": code, "message": message, "detail": detail}}


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(APIError)
    async def _api(_: Request, exc: APIError) -> JSONResponse:
        return JSONResponse(status_code=exc.status_code,
                            content=_envelope(exc.code, exc.message, exc.detail))

    @app.exception_handler(RequestValidationError)
    async def _validation(_: Request, exc: RequestValidationError) -> JSONResponse:
        return JSONResponse(status_code=422,
                            content=_envelope("VALIDATION_ERROR", "Request validation failed", exc.errors()))

    @app.exception_handler(StarletteHTTPException)
    async def _http(_: Request, exc: StarletteHTTPException) -> JSONResponse:
        message = exc.detail if isinstance(exc.detail, str) else "HTTP error"
        detail = exc.detail if not isinstance(exc.detail, str) else None
        return JSONResponse(status_code=exc.status_code,
                            content=_envelope(f"HTTP_{exc.status_code}", message, detail))

    @app.exception_handler(Exception)
    async def _unhandled(_: Request, exc: Exception) -> JSONResponse:
        logger.exception("unhandled exception: %s", exc)
        return JSONResponse(status_code=500,
                            content=_envelope("INTERNAL", "Internal server error", None))
