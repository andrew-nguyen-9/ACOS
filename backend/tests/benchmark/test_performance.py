"""Performance benchmarks for pure, I/O-free core functions.

Run separately from the main suite:
    pytest backend/tests/benchmark/ --benchmark-only
"""
from backend.ingestion.security import sanitize_filename
from backend.services.copilot.engine import _detect_intent, _format_history


LONG_HISTORY = [
    {"role": "user", "content": f"message {i}"}
    for i in range(20)
]


def test_bench_sanitize_filename_normal(benchmark):
    benchmark(sanitize_filename, "my_resume_v2.pdf")


def test_bench_sanitize_filename_traversal(benchmark):
    benchmark(sanitize_filename, "../../../etc/passwd")


def test_bench_detect_intent_resume(benchmark):
    benchmark(_detect_intent, "Can you help me tailor my resume for this role?")


def test_bench_detect_intent_no_match(benchmark):
    benchmark(_detect_intent, "hello world this is an unrelated query")


def test_bench_format_history_empty(benchmark):
    benchmark(_format_history, [])


def test_bench_format_history_long(benchmark):
    # Should truncate to last 5 turns — verify this stays O(1) on large history
    benchmark(_format_history, LONG_HISTORY)
