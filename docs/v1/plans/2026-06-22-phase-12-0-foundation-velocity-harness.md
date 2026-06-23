# Phase 12.0 — Foundation: Perf Harness + Token-Efficient Workflow

**Track:** Shared · **Depends on:** Phase 11 complete · **Branch:** `feat/phase-12-velocity-flywheel-multitenant`
**Status:** Planned

> Read `2026-06-22-phase-12-roadmap.md` first. Gates every later segment. No feature code here.

## 1. Context

Phase 11.0 built `scripts/perf/startup_bench.py` + pytest-benchmark gates and `docs/PERFORMANCE_LOG.md`.
Phase 12 introduces latency surfaces Phase 11 never measured: TTFT (live Ollama), ingestion
throughput, async-vs-sync request latency. We extend the harness before changing anything, so every
velocity segment has a before/after number.

We also **clean the dependency base before building on it.** On the first Phase 12 push, GitHub
Dependabot flagged **41 open alerts (3 high, 32 medium, 6 low)** on the repo. Foundation segment =
clean foundation, so triage lands here.

## 2. Goals

- Re-baseline existing Phase 11 metrics on the current machine; record in `PERFORMANCE_LOG.md`.
- Add **TTFT bench** and **ingestion-throughput bench** (live-Ollama, opt-in via env flag so CI without
  Ollama still passes — `# ponytail: skip if OLLAMA_LIVE unset`).
- Add an **async request-latency bench** harness slot (used by 12.2) measuring p50/p95 under N
  concurrent requests.
- Document the token-efficient dev workflow (RTK/Caveman/Ponytail/Superpowers) in
  `docs/OPTIMIZATION_SYSTEM.md` as the Phase 12 working agreement.
- **Triage + remediate the 41 Dependabot alerts** (see §4b), prioritizing the user-input attack
  surface (`python-multipart` uploads, `pypdf` ingestion) over dev-only deps.

## 3. Non-goals (YAGNI)

- No optimization yet — measurement only.
- No CI infra for live Ollama; live benches are dev-run, results pasted into the log/PR.
- Dependency triage does **not** add new app-side PDF/upload hardening logic — that already exists
  (CLAUDE.md security reqs + Phase 11.1 ingestion retry/dead-letter). 12.0 bumps versions and
  documents residual risk; any code-level mitigation a pinned-out CVE still needs is filed as a
  follow-up, not done inline.

## 4. Acceptance criteria

- [ ] `scripts/perf/ttft_bench.py` reports TTFT median/p95 against live Ollama; skips cleanly when `OLLAMA_LIVE` unset.
- [ ] `scripts/perf/ingest_bench.py` reports per-PDF ingest time; skips cleanly without Ollama.
- [ ] Phase 11 metrics re-baselined; new baseline rows appended to `docs/PERFORMANCE_LOG.md` dated 2026-06-22.
- [ ] `docs/OPTIMIZATION_SYSTEM.md` has a "Phase 12 token-efficient workflow" section.
- [ ] All existing tests green; no source behavior changed.
- [ ] All **3 high** alerts resolved (upgrade or documented compensating control).
- [ ] `python-multipart`, `pypdf`, `requests` bumped to patched versions; `pip install` + full suite green after bump.
- [ ] Remaining alerts each marked **fixed / accepted-with-rationale / deferred-with-ticket** in `docs/SECURITY_DEPENDENCIES.md`.
- [ ] Dependabot high-severity count = 0 after the PR merges (re-check the alerts page).

## 4b. Dependency vulnerability triage

Alert landscape (Dependabot, 2026-06-22 — re-pull at start, numbers drift):

| Package | Alerts | Severity | Surface | Action |
|---------|-------:|----------|---------|--------|
| `python-multipart` | 7 | **3 high** + 1 med + 3 low | FastAPI multipart upload parsing — DoS + arbitrary file write | **Upgrade (priority 1).** Real attack surface even local (the upload endpoints). |
| `pypdf` | 30 | 30 med/low | PDF ingestion — malicious-PDF RAM exhaustion / infinite loops | **Upgrade (priority 1).** ACOS ingests user PDFs; ties to CLAUDE.md "never crash on malformed files". |
| `requests` | 2 | medium | netrc credential leak, insecure temp-file reuse | Upgrade. |
| `pytest` | 1 | medium | dev-only (tmpdir handling) | Upgrade dev dep; low urgency, no runtime exposure. |
| `glib` (Rust) | 1 | medium | transitive (Tauri) iterator soundness | `cargo update` if a patched semver exists; else document + defer (transitive). |

Approach (Ponytail rung order):
1. `pip install -U python-multipart pypdf requests pytest` within compatible constraints; `cargo update -p glib`.
2. Run the full suite + the new benches — confirm no behavior/parse regression (pypdf API can shift between majors; pin a tested version, `# ponytail: pin exact tested version, not a floating range`).
3. Anything that can't be upgraded without breaking → record in `docs/SECURITY_DEPENDENCIES.md` with the CVE, why it's deferred, and the compensating control already in place (e.g. ingestion size limits + retry/dead-letter from 11.1 blunt the pypdf DoS class).
4. This is a `security-review`-gated step, not a perf step — review the multipart/pypdf bumps for behavior change.

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
EDIT pyproject.toml / requirements         (bump python-multipart, pypdf, requests, pytest)
EDIT frontend/src-tauri/Cargo.lock         (cargo update glib if patched)
NEW  docs/SECURITY_DEPENDENCIES.md          (triage table: fixed / accepted / deferred per alert)
```

## 7. Test plan (TDD)

- `test_async_latency.py`: asserts the harness runs and returns p50/p95 numbers on the sync baseline.
- Bench scripts: smoke-tested with `OLLAMA_LIVE` unset → exit 0 with "skipped".

## 8. Plugin orchestration checklist

- [ ] `superpowers:verification-before-completion` (numbers must be real, pasted, dated).
- [ ] `context7` — pytest-benchmark API if extended; patched version ranges for python-multipart/pypdf/requests.
- [ ] RTK confirmed active (`rtk --version`); Caveman/Ponytail confirmed on.
- [ ] `security-review` — review the python-multipart + pypdf upgrades for parse-behavior change.
- [ ] `gh api .../dependabot/alerts` to re-pull the live list at start and confirm zero-high at end.

## 9. Perf budget impact

None (measurement only). Establishes the gates the rest of Phase 12 is held to. Dependency bumps must
not regress the re-baselined numbers (verify after upgrading).

## 10. Definition of Done

Harness extended, baselines re-recorded, workflow documented, **Dependabot high-severity count = 0
with all alerts triaged in `SECURITY_DEPENDENCIES.md`**, tests green, PR with the baseline table +
the dependency triage summary.
