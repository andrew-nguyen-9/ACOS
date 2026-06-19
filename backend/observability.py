from __future__ import annotations

import logging
import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

_perf_log = logging.getLogger("acos.perf")
_op_log = logging.getLogger("acos.op")


class TimingMiddleware(BaseHTTPMiddleware):
    """Adds ``X-Process-Time-Ms`` header and emits a structured perf log line."""

    async def dispatch(self, request: Request, call_next) -> Response:
        start = time.perf_counter()
        response = await call_next(request)
        elapsed_ms = (time.perf_counter() - start) * 1000
        header_val = f"{elapsed_ms:.2f}"
        response.headers["X-Process-Time-Ms"] = header_val
        _perf_log.info(
            "method=%s path=%s status=%s ms=%s",
            request.method,
            request.url.path,
            response.status_code,
            header_val,
        )
        return response


def log_operation(op: str, **kwargs: object) -> None:
    """Emit a structured log line to the ``acos.op`` logger.

    Example::

        log_operation("resume_generate", resume_id="abc", bullets=4)
        # → INFO  acos.op  op=resume_generate resume_id=abc bullets=4
    """
    parts = [f"op={op}"] + [f"{k}={v}" for k, v in kwargs.items()]
    _op_log.info(" ".join(parts))
