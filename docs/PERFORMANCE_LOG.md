# Performance Log

Tracks ACOS performance baselines and per-segment regression checks. Phase 11.0
built the harness; every later segment **appends a row** proving it did not
regress (budget = baseline + 10%, see `docs/superpowers/plans/2026-06-21-phase-11-roadmap.md`).

Numbers are machine-dependent — compare **deltas on the same machine**, not
absolutes. Baseline machine: `macOS-26.5.1-arm64` (Apple Silicon), Python 3.12.13.

## How to run the harness

```bash
# Backend cold start (median/p95 of N cold imports → create_app ready)
python scripts/perf/startup_bench.py --n 5     # writes scripts/perf/baselines/startup.json

# Backend orchestration benches (LLM mocked — measures our code, not Ollama)
pytest backend/tests/benchmark -q --benchmark-only

# Frontend bundle size
cd frontend && npm run build                   # read the gzipped index size
```

## Baseline — 2026-06-21 (Phase 11.0)

| Metric | Baseline | Budget (≤) | Measured by |
|--------|----------|-----------|-------------|
| Backend cold start — median | 707 ms | 778 ms | `scripts/perf/startup_bench.py` (n=5) |
| Backend cold start — p95 | 1083 ms | 1191 ms | `scripts/perf/startup_bench.py` (n=5) |
| `resume/generate` median (mocked LLM) | 0.32 ms | 0.35 ms | `test_resume_generate_bench.py` |
| copilot chat median (mocked LLM) | 0.008 ms | 0.009 ms | `test_copilot_bench.py` |
| Frontend initial JS bundle (gzipped) | 70.3 kB | 80.8 kB (+15%) | `vite build` (`dist/assets/index-*.js`) |
| Frontend idle FPS | ≥ 60 (target 120 ProMotion) | ≥ 60 | FPS dev overlay |

> Mocked-LLM benches measure **orchestration overhead only**. Real end-to-end
> latency with live Ollama is tracked separately in Phase 11.3.

### Legacy targets (LLM online, informational)

| Operation | p50 target | p95 target |
|-----------|-----------|-----------|
| resume/generate (LLM online) | < 8 000 ms | < 15 000 ms |
| resume/generate (offline fallback) | < 200 ms | < 500 ms |
| cover_letter/generate (LLM online) | < 10 000 ms | < 20 000 ms |
| BulletScorer.score_many (100 bullets) | < 5 ms | < 20 ms |
| LayoutEngine.estimate_resume | < 1 ms | < 5 ms |

## Frontend interaction trace procedure (manual)

The FPS overlay gives a live idle reading; for jank (long tasks > 50 ms during
a scripted interaction) capture a trace:

1. `cd frontend && npm run dev`, open the app with `?perf=1` (or toggle the
   overlay with **Cmd+Shift+P**). Confirm idle FPS ≥ 60.
2. Open Chrome DevTools → **Performance** → record.
3. Perform the scripted interaction (e.g. open Copilot, send a message; or
   navigate Dashboard → Resume → Cover Letter).
4. Stop recording. Read **Long Tasks** (red-flagged, > 50 ms) — budget is **0**
   during animations. The overlay's `measureLongTasks()` also console-warns each.
5. Record before/after numbers in the segment's PR. `markInteraction(name)`
   (`frontend/src/utils/perf.ts`) drops User Timing marks to align the trace.

## Per-segment regression log

| Date | Segment | Metric | Baseline | Measured | Pass? |
|------|---------|--------|----------|----------|-------|
| 2026-06-21 | 11.0 | (harness established — baselines above) | — | — | — |
| 2026-06-21 | 11.1 | resume/generate median (mocked LLM) | 0.32 ms | 0.32 ms | ✅ |
| 2026-06-21 | 11.1 | copilot chat median (mocked LLM) | 0.008 ms | 0.008 ms | ✅ |
