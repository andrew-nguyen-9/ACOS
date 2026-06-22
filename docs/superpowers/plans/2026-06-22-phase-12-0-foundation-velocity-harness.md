# Phase 12.0 — Foundation: Perf Harness + Token-Efficient Workflow

**Track:** Shared · **Depends on:** Phase 11 complete · **Branch:** `feat/phase-12-velocity-flywheel-multitenant`
**Status:** Planned

> Read `2026-06-22-phase-12-roadmap.md` first. Gates every later segment. No feature code here.

## 1. Context

Phase 11.0 built `scripts/perf/startup_bench.py` + pytest-benchmark gates and `docs/PERFORMANCE_LOG.md`.
Phase 12 introduces latency surfaces Phase 11 never measured: TTFT (live Ollama), ingestion
throughput, async-vs-sync request latency. We extend the harness before changing anything, so every
velocity segment has a before/after number.

## 2. Goals

- Re-baseline existing Phase 11 metrics on the current machine; record in `PERFORMANCE_LOG.md`.
- Add **TTFT bench** and **ingestion-throughput bench** (live-Ollama, opt-in via env flag so CI without
  Ollama still passes — `# ponytail: skip if OLLAMA_LIVE unset`).
- Add an **async request-latency bench** harness slot (used by 12.2) measuring p50/p95 under N
  concurrent requests.
- Document the token-efficient dev workflow (RTK/Caveman/Ponytail/Superpowers) in
  `docs/OPTIMIZATION_SYSTEM.md` as the Phase 12 working agreement.

## 3. Non-goals (YAGNI)

- No optimization yet — measurement only.
- No CI infra for live Ollama; live benches are dev-run, results pasted into the log/PR.

## 4. Acceptance criteria

- [ ] `scripts/perf/ttft_bench.py` reports TTFT median/p95 against live Ollama; skips cleanly when `OLLAMA_LIVE` unset.
- [ ] `scripts/perf/ingest_bench.py` reports per-PDF ingest time; skips cleanly without Ollama.
- [ ] Phase 11 metrics re-baselined; new baseline rows appended to `docs/PERFORMANCE_LOG.md` dated 2026-06-22.
- [ ] `docs/OPTIMIZATION_SYSTEM.md` has a "Phase 12 token-efficient workflow" section.
- [ ] All existing tests green; no source behavior changed.

## 5. Design

- `scripts/perf/ttft_bench.py`: fire one warm + N cold `generate` calls via `ollama_client`, time
  first streamed byte (uses the 12.4 streaming path once it exists; until then times first response).
- `scripts/perf/ingest_bench.py`: run the ingestion pipeline on a fixed sample PDF in `examples/`, time end-to-end.
- Reuse `pytest-benchmark` registration pattern from Phase 11.

## 6. File-level plan

```
NEW  scripts/perf/ttft_bench.py
NEW  scripts/perf/ingest_bench.py
EDIT scripts/perf/startup_bench.py        (re-run; no code change unless drift)
EDIT docs/PERFORMANCE_LOG.md              (2026-06-22 baseline rows)
EDIT docs/OPTIMIZATION_SYSTEM.md          (Phase 12 workflow section)
NEW  backend/tests/benchmark/test_async_latency.py  (placeholder harness for 12.2)
```

## 7. Test plan (TDD)

- `test_async_latency.py`: asserts the harness runs and returns p50/p95 numbers on the sync baseline.
- Bench scripts: smoke-tested with `OLLAMA_LIVE` unset → exit 0 with "skipped".

## 8. Plugin orchestration checklist

- [ ] `superpowers:verification-before-completion` (numbers must be real, pasted, dated).
- [ ] `context7` — pytest-benchmark API if extended.
- [ ] RTK confirmed active (`rtk --version`); Caveman/Ponytail confirmed on.

## 9. Perf budget impact

None (measurement only). Establishes the gates the rest of Phase 12 is held to.

## 10. Definition of Done

Harness extended, baselines re-recorded, workflow documented, tests green, PR with the baseline table.
