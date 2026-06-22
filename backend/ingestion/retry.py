"""Bounded retry with exponential backoff (Phase 11.1).

Pure helper, no external dependency. Retries only the configured exception
types; anything else (e.g. PermanentError) propagates on the first raise.
`sleep` is injectable so tests run instantly.
"""
from __future__ import annotations

import time
from typing import Callable, TypeVar

from backend.ingestion.errors import TransientError

T = TypeVar("T")


def retry(
    fn: Callable[[], T],
    *,
    attempts: int = 3,
    base_delay: float = 0.2,
    max_delay: float = 2.0,
    exc: type[BaseException] | tuple[type[BaseException], ...] = TransientError,
    sleep: Callable[[float], None] = time.sleep,
) -> T:
    """Call `fn`, retrying on `exc` up to `attempts` times.

    Backoff before retry n (0-indexed) is `min(base_delay * 2**n, max_delay)`.
    Re-raises the last exception once attempts are exhausted.
    """
    last_exc: BaseException | None = None
    for i in range(attempts):
        try:
            return fn()
        except exc as e:  # type: ignore[misc]
            last_exc = e
            if i == attempts - 1:
                break
            sleep(min(base_delay * (2 ** i), max_delay))
    assert last_exc is not None  # only reachable after a caught exception
    raise last_exc
