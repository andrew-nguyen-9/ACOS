# Phase 11.0 — Foundation & Performance Budget Harness

**Track:** Shared · **Depends on:** Phase 10 complete · **Branch:** `feat/phase-11-hardening-and-frontend`
**Status:** Planned

> Read `2026-06-21-phase-11-roadmap.md` first for the global rules and budget table.

---

## 1. Context

Phase 11 promises "performance is never sacrificed." That promise is unenforceable without a
baseline. 11.0 builds the measurement harness **before** any hardening or UI work, so every
later segment can prove it did not regress. It is deliberately small and dependency-free.

Current seams:
- `backend/observability.py` — `TimingMiddleware` (adds `X-Response-Time`) + `log_operation()`.
- `backend/tests/benchmark/` — exists (pytest-benchmark already used in repo).
- `docs/PERFORMANCE_LOG.md` — exists (837B), currently near-empty.
- No persisted metrics table; no frontend FPS instrumentation.

## 2. Goals

- A repeatable **backend perf bench** that records startup time, `/resume/generate` p95, and
  copilot first-token latency (LLM mocked) to a committed baseline file.
- A **frontend FPS dev overlay** + a documented manual procedure for capturing interaction
  traces (idle FPS, long-task count during a scripted interaction).
- A single **`docs/PERFORMANCE_LOG.md`** format that every segment appends to.
- A `scripts/perf/` directory with runnable benches and a `make perf` / documented command.

## 3. Non-goals (YAGNI)

- No CI integration / no automated regression failure gate (manual attach-to-PR is enough now).
- No production telemetry upload (local-only per ADR-001).
- No drift dashboards — that is 11.2 (observability) territory.
- No Grafana/Prometheus. Plain JSON + markdown.

## 4. Acceptance criteria

- [ ] `python scripts/perf/startup_bench.py` prints cold-start ms (median of N runs) and writes JSON.
- [ ] `pytest backend/tests/benchmark -q` runs resume-generate + copilot benches with mocked LLM and passes.
- [ ] Frontend dev build shows an FPS overlay (toggle via `?perf=1` or `Cmd+Shift+P`) that reports rolling FPS; absent in production build.
- [ ] `docs/PERFORMANCE_LOG.md` has a baseline table with the metrics from the roadmap budget table, dated 2026-06-21.
- [ ] `docs/superpowers/plans/2026-06-21-phase-11-roadmap.md` budget numbers are filled in with real baselines (replace "baseline" placeholders).
- [ ] All existing tests still pass; coverage not reduced.

## 5. Design

### Backend bench
- `scripts/perf/startup_bench.py`: spawns `python -c "import backend.main"` (or imports in-proc),
  times to `create_app()` ready, repeats N=5, reports median/p95, writes `scripts/perf/baselines/startup.json`.
- `backend/tests/benchmark/test_resume_generate_bench.py`: uses pytest-benchmark; LLM via existing
  `OllamaClient` mocked to a fixed-latency stub (so the bench measures *our* code, not Ollama).
- `backend/tests/benchmark/test_copilot_bench.py`: same pattern, copilot engine first-token path.
- A tiny helper `backend/tests/benchmark/_mock_llm.py` providing a deterministic mock client.

### Frontend FPS overlay
- `frontend/src/components/dev/FpsOverlay.tsx`: `requestAnimationFrame` loop computing rolling
  FPS using a `useRef` ring buffer (NOT state — see PERF-RP-001); renders only ~2×/sec via a
  throttled state commit. Mounted in `App.tsx` only when `import.meta.env.DEV` and `?perf=1`.
- `frontend/src/utils/perf.ts`: `markInteraction(name)` + `measureLongTasks()` wrapping
  `PerformanceObserver({entryTypes:['longtask']})`; logs to console table.
- Document the manual trace procedure in `docs/PERFORMANCE_LOG.md` (how to capture before/after).

### Baseline capture
- Run all benches once, paste medians into `PERFORMANCE_LOG.md` and the roadmap budget table.

## 6. File-level plan

```
NEW  scripts/perf/__init__.py
NEW  scripts/perf/startup_bench.py
NEW  scripts/perf/baselines/.gitkeep
NEW  backend/tests/benchmark/_mock_llm.py
NEW  backend/tests/benchmark/test_resume_generate_bench.py
NEW  backend/tests/benchmark/test_copilot_bench.py
NEW  frontend/src/components/dev/FpsOverlay.tsx
NEW  frontend/src/utils/perf.ts
EDIT frontend/src/App.tsx           (mount FpsOverlay in DEV when ?perf=1)
EDIT docs/PERFORMANCE_LOG.md        (baseline table + trace procedure)
EDIT docs/superpowers/plans/2026-06-21-phase-11-roadmap.md  (fill budget numbers)
```

## 7. Test plan (TDD)

- `test_startup_bench.py` (unit): asserts `startup_bench.run(n=2)` returns dict with `median_ms>0`
  and writes a valid JSON file to a tmp path.
- Bench tests double as their own verification (they must execute the real code paths with the mock).
- Frontend: a Vitest/RTL test is overkill here; instead a `perf.ts` self-check asserting the ring
  buffer averages correctly (`utils/perf.test.ts` if a test runner exists, else a `// ponytail:` note).
- Manual: confirm overlay shows ≥60 in dev, and is tree-shaken out of `vite build` (grep dist).

## 8. Plugin orchestration checklist (CLAUDE.md rule 5)

- [ ] `context7` for any pytest-benchmark / PerformanceObserver API specifics.
- [ ] `superpowers:test-driven-development` for the bench/util tests.
- [ ] `superpowers:verification-before-completion` — run benches, paste real output into PR.
- [ ] `security-guidance` — N/A (no I/O of user data), note in PR.

## 9. Perf budget impact

This segment *defines* the budgets. The overlay must itself cost <1ms/frame and be DEV-only.

## 10. Risks & mitigations

- *Mock LLM hides real latency* → explicit: benches measure our orchestration overhead, not model;
  document that. Real-model latency tracked separately in 11.3 with live Ollama.
- *Machine-dependent baselines* → record machine + store JSON; compare deltas not absolutes.

## 11. Definition of Done

Benches runnable and committed; baseline numbers in `PERFORMANCE_LOG.md` and roadmap; FPS overlay
works in dev and is absent in prod; all tests green; PR opened with baseline output attached.
