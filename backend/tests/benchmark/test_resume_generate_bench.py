"""Perf bench: POST /resume/generate orchestration path (LLM mocked).

Measures our pipeline (evidence scoring → selection → rewrite → layout →
validate → ATS → persist), not Ollama. Run with:
    pytest backend/tests/benchmark -q --benchmark-only
"""
from backend.tests.benchmark._mock_llm import build_resume_generator

_JD = "Senior Python data engineering role at Acme building ETL pipelines."


def test_bench_resume_generate(benchmark, test_session):
    gen = build_resume_generator(test_session)

    result = benchmark(gen.generate, _JD, "software")

    # Sanity: the path actually produced a resume, so the timing is meaningful.
    assert "resume_id" in result
    assert "ats_score" in result
