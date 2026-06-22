"""Perf bench: copilot first-token / chat path (RAG + LLM mocked).

Measures intent detection + history formatting + result assembly overhead.
Run with:
    pytest backend/tests/benchmark -q --benchmark-only
"""
from backend.tests.benchmark._mock_llm import build_copilot_engine

_HISTORY = [{"role": "user", "content": f"message {i}"} for i in range(10)]


def test_bench_copilot_chat(benchmark):
    engine = build_copilot_engine()

    result = benchmark(
        engine.chat,
        "Can you help me tailor my resume for this role?",
        _HISTORY,
    )

    assert result["intent"] == "resume_help"
    assert result["citations"]
