# Performance Log

Tracks generation latency benchmarks across releases.

| Date | Operation | p50 (ms) | p95 (ms) | Model | Notes |
|------|-----------|----------|----------|-------|-------|
| 2026-06-20 | resume/generate | — | — | qwen3:8b | Baseline before Phase 8.1 |
| 2026-06-20 | cover_letter/generate | — | — | qwen3:8b | Baseline before Phase 8.1 |

Update after each release using `backend/tests/benchmark/test_performance.py`.

## Targets

| Operation | p50 target | p95 target |
|-----------|-----------|-----------|
| resume/generate (LLM online) | < 8 000 ms | < 15 000 ms |
| resume/generate (offline fallback) | < 200 ms | < 500 ms |
| cover_letter/generate (LLM online) | < 10 000 ms | < 20 000 ms |
| BulletScorer.score_many (100 bullets) | < 5 ms | < 20 ms |
| LayoutEngine.estimate_resume | < 1 ms | < 5 ms |
