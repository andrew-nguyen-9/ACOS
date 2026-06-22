"""TDD for the ingestion retry helper (Phase 11.1)."""
import pytest

from backend.ingestion.errors import PermanentError, TransientError
from backend.ingestion.retry import retry


def _flaky(fail_times: int, exc=TransientError):
    """Return a callable that raises `exc` the first `fail_times` calls then returns 'ok'."""
    state = {"calls": 0}

    def fn():
        state["calls"] += 1
        if state["calls"] <= fail_times:
            raise exc("transient")
        return "ok"

    fn.state = state  # type: ignore[attr-defined]
    return fn


def test_succeeds_after_k_failures():
    fn = _flaky(2)
    result = retry(fn, attempts=3, base_delay=0, sleep=lambda _: None)
    assert result == "ok"
    assert fn.state["calls"] == 3


def test_gives_up_after_n_attempts_raising_last():
    fn = _flaky(5)
    with pytest.raises(TransientError):
        retry(fn, attempts=3, base_delay=0, sleep=lambda _: None)
    assert fn.state["calls"] == 3


def test_permanent_error_not_retried():
    fn = _flaky(5, exc=PermanentError)
    with pytest.raises(PermanentError):
        retry(fn, attempts=3, base_delay=0, sleep=lambda _: None)
    assert fn.state["calls"] == 1  # no retry on non-transient


def test_backoff_is_bounded_and_exponential():
    delays: list[float] = []
    fn = _flaky(5)
    with pytest.raises(TransientError):
        retry(
            fn,
            attempts=4,
            base_delay=0.1,
            max_delay=0.25,
            sleep=delays.append,
        )
    # 3 sleeps between 4 attempts; exponential then capped at max_delay.
    assert delays == [0.1, 0.2, 0.25]


def test_success_first_try_no_sleep():
    delays: list[float] = []
    result = retry(lambda: "ok", attempts=3, base_delay=0.1, sleep=delays.append)
    assert result == "ok"
    assert delays == []
