# Phase 12.9 — Architecture Spikes: Findings

**Date:** 2026-06-22 · **Branch:** `feat/phase-12-velocity-flywheel-multitenant`
**Spec:** `docs/v1/plans/2026-06-22-phase-12-9-architecture-spikes.md`
**Machine:** macOS-26.5.1-arm64 · Python 3.12.13 · Ollama live (qwen3:8b + nomic-embed-text)

This doc records **all six** outcomes regardless of verdict (spec §4, §10). Each was gated by a
`context7` viability check **before** any bench (laziness ladder rung 1: "does this need to exist for a
single-user local app?"). Throwaway benches live under `scripts/perf/spikes/` (not shipped; faiss-cpu /
msgpack are **not** in `backend/requirements.txt`). **No production code changed. No ADRs (zero adopts).**

| # | Spike | Viability (context7) | Verdict | Headline number |
|---|-------|----------------------|---------|-----------------|
| S1 | msgpack IPC | `msgpack` 1.2.1 + Rust `rmp-serde` exist | **DEFER** | 2.98× codec, saves **0.53 ms/req** |
| S2 | FAISS vector store | faiss-cpu 1.14.3 arm64 wheel; binary + float indexes | **DEFER** (float) / **REJECT** (binary leg) | float recall 0.991 / binary recall **0.765** |
| S3 | Nuitka packaging | `--macos-create-app-bundle` exists | **DEFER** (notes only) | floor is import-bound **598 ms**, Nuitka can't move it |
| S4 | PyO3 singularity | feasibility-only | **REJECT → Phase 13** | n/a (zero code) |
| ADV-a | Pinned unified memory | OS/Metal lever, Ollama-owned | **DEFER** (zero code) | Ollama owns model RAM, not our sidecar |
| ADV-b | JIT rerank (Numba/Jax) | Numba/Jax exist | **REJECT** | rerank() = **20–97 µs**, no matrix to JIT |

Default leans (speculative-plan ledger §B) were `defer`/`reject` for all six; every gate that could be
measured was, and none cleared. Production stack (HTTP-JSON, Chroma, PyInstaller, FastAPI) **unchanged**.

---

## S1 — IPC format: JSON vs msgpack → **DEFER**

**Bench:** `scripts/perf/spikes/ipc_msgpack_bench.py --n 2000` (pure-CPU, seed 1209, best-of-3).
Payload = a ~100 k-char generated-document response (prose body + metadata + evidence-chunk list),
the kind that crosses the Tauri↔backend HTTP boundary (lib.rs spawns the FastAPI sidecar; transport is
HTTP-JSON — this is a **codec microbench, not a new transport**, spec §3).

| codec | bytes | serialize (µs) | deserialize (µs) | round-trip (µs) |
|-------|------:|---------------:|-----------------:|----------------:|
| JSON | 144 338 | 468.5 | 321.9 | 790.4 |
| msgpack | 135 029 | 84.9 | 180.5 | 265.4 |

msgpack is **2.98× faster** on round-trip codec and **6% smaller** on the wire — but the absolute saving
is **0.53 ms/request**.

**Gate (12.9.1):** ≥30% serialize/parse win that shows up **end-to-end** *and* a perceptible reduction in
token-stream stutter. The codec ratio passes 30%, but the **absolute** 0.53 ms is invisible against a
request whose generation time is hundreds of ms to seconds (TTFT 347 ms warm → multi-second reasoning,
12.5). It cannot perceptibly reduce stream stutter because JSON codec was never the frame-stall source.

**Why defer, not adopt (Ponytail rung 1):** for one local user, per-request codec cost is already
negligible; HTTP-JSON keeps `curl` + network-panel debuggability and a single transport. msgpack would
add dual-format maintenance + Rust-side decode for a sub-millisecond, end-to-end-invisible win. **Reopen
only** if 12.4 streaming profiling later shows JSON parse as a *measured* frame-stall source.

---

## S2 — Vector store: Chroma vs FAISS float vs FAISS binary-quant → **DEFER (float) / REJECT (binary)**

**Bench:** `scripts/perf/spikes/vector_faiss_bench.py` (seed 1209, dim 768 = nomic-embed-text).
Synthetic random vectors have no cluster structure → top-k is near-tied noise and recall is meaningless
there (latency/memory still valid); the recall verdict uses the **live** arm (`OLLAMA_LIVE=1`, real
nomic embeddings of seeded sentences, genuine NN structure). Recall reference = Chroma top-k (the
production store, which 12.6 consolidated to ONE collection); FAISS-float exact = ground truth for binary.

**Live, n=1000, q=50, k=15, real nomic embeddings:**

| store | build (ms) | query (ms/q) | recall@15 | mem (MB) |
|-------|-----------:|-------------:|----------:|---------:|
| Chroma (cosine, reference) | 319.2 | 0.259 | 1.000 (ref) | 3.07 |
| FAISS IndexFlatIP (float exact) | 1.3 | 0.088 | **0.991** vs Chroma | 3.07 |
| FAISS IndexBinaryFlat (Hamming) | 0.3 | 0.019 | **0.765** vs exact / 0.764 vs Chroma | **0.096** (32× smaller) |

(Synthetic arm `--n 2000`: same shape — FAISS float query 0.297 ms vs Chroma 0.622 ms, binary 32× smaller;
recall numbers there are noise, as expected for structureless vectors.)

**FAISS float → DEFER.** Recall parity holds (0.991, confirming both are ~exact) and query is ~3× faster
(0.088 vs 0.259 ms) — but both are **sub-millisecond** and memory is **identical**. The 12.9.2 gate wants a
*material* latency/memory win; 0.17 ms/query for one user is not material, and Chroma's 12.6 consolidation
already removed the "10 collections is heavy" pain this spike reacted to. Adoption cost is High (adapter +
shadow-read parity + preserve 12.7 FTS5 leg + 12.14 tenant isolation + data migration) for an immaterial
win. **Reopen only** if post-12.6 Chroma footprint/latency becomes a *measured* problem.

**FAISS binary-quant → REJECT.** Recall **0.765** is far below the 0.98 tolerance — binary quantization
loses ~24% of relevant results to buy 32× memory. For a single user the float corpus is ~3 MB (≈30 MB at
10 k chunks); the memory it saves is RAM nobody is short of. Trading a quarter of retrieval relevance for
a few MB is a clear reject (spec trap 3: a memory win that tanks recall is a reject). A Hamming
*prefilter → float rerank* hybrid could lift recall back, but that is exactly the complexity Ponytail
refuses when the float index is already this small.

---

## S3 — Packaging: Nuitka vs PyInstaller → **DEFER (notes only, no build)**

Full write-up: `scripts/perf/spikes/nuitka_coldstart_notes.md`.

`context7` confirms Nuitka can build a macOS app bundle (`--macos-create-app-bundle` / `--mode=app`). But
cold start is **import-bound, not interpreter-startup-bound** (12.3): reference median **597.96 ms**
(`baselines/startup.json`). Per-module self import-time this session: sqlalchemy **151.8 ms**, fastapi
**134.2 ms**, pydantic 35.0 ms, pydantic_core 16.9 ms, lxml 17.5 ms. Much of that is **C-extension module
init** (pydantic_core/Rust, lxml/libxml2) Nuitka does **not** recompile, plus SQLAlchemy/Pydantic
registration work that runs identically as Nuitka-C. Nuitka speeds up pure-Python execution — not the part
of the 600 ms that dominates — so the expected win is a modest glue-code shave, not a step change.

Against that: a C-toolchain minutes-scale compile of the whole backend, plus untested code-signing /
notarization of a Nuitka bundle. **DEFER** — reopen only if the ≤400 ms cold-start budget (12.0) is still
missed after 12.3 (it is not a measured production problem). No build performed; PyInstaller
(`acos-backend.spec`) remains the path.

---

## S4 — PyO3 singularity (merge Python into the Rust binary) → **REJECT → Phase 13**

Feasibility study only — **no Rust, no FastAPI deletion, zero code** (spec trap 4). PyO3 can embed a
CPython interpreter in a Rust binary, so it is technically *possible*. It is rejected on cost, not
feasibility:

- **Deletes the HTTP boundary** — loses `curl` / network-panel debuggability and the clean
  route→service→repo layering (11.3 observability); the sidecar would become an in-process FFI blob.
- **Couples release cadence** — Python and Rust must now ship as one artifact; no independent backend iteration.
- **Enormous rewrite** for a latency win that **12.2–12.6 already capture** (async runtime, cold-start
  lazy imports, embed batching, Chroma consolidation) without touching the architecture.

**Ponytail rung 1:** a single-user local app does not need to delete its own debuggable HTTP layer to save
IPC microseconds it is not spending. Recorded as **reject for Phase 12 → escalate to a Phase 13 epic if
ever** (its own brainstorm + ADR + migration plan, not a 12.9.x sub-segment). Ledger row → `reject (→ Phase 13)`.

---

## ADV-a — Pinned unified-memory pages → **DEFER (zero code)**

The idea: pin memory pages to prevent swap-out during LLM generation pauses. **It does not apply to our
process.** The model weights + KV cache live in **Ollama's** address space, not the Python sidecar
(12.5 trap 1: `lib.rs` spawns the *Python* sidecar, not Ollama; daemon/model memory tuning lives in
`scripts/setup_ollama.sh` + `MODEL_SETUP.md`). Our Python process holds no model memory worth pinning, and
we cannot pin pages we do not own.

12.5 already addressed swap pressure at the right layer: `num_ctx` calibration (2048→4096 dynamic),
KV-cache q8_0 quant, sequential embedder unload, `keep_alive` tuning. `ollama ps` after 12.5 showed only
qwen3 resident (5.3 GB) with nomic evicted — no measured swap cliff. **DEFER** — reopen only if 12.5 leaves
a *measured* swap event on 16 GB during generation, and even then the lever belongs in Ollama/OS config,
not our code. `# ponytail: pinning is a swap band-aid; the real fix is fitting in budget (12.5 does).`

---

## ADV-b — JIT-compiled reranking (Numba/Jax) → **REJECT**

**Bench:** `scripts/perf/spikes/rerank_jit_bench.py` (seed 1209, best-of-3). The brief proposes JITting
"the reranking distance matrix." **Post-12.7 there is no distance matrix in the reranker.**
`backend/rag/reranker.py` `rerank()` (lines 31–45) is a pure-Python **scalar fusion loop** over the
already-retrieved candidate set — dense similarity is computed upstream in Chroma's C++, the lexical leg in
SQLite FTS5. The reranker just fuses two normalized scalars × confidence × outcome boost.

| candidate set | rerank() per call |
|---------------|------------------:|
| 50 (realistic post-retrieval) | **20.1 µs** |
| 200 | 97.3 µs |

A Numba/Jax **first-call compile is hundreds of ms to seconds** — ~1000–10000× the entire per-call cost,
just to warm up. There is no array kernel for it to accelerate. **REJECT** (Ponytail: the thing the spike
optimizes doesn't exist in our code; the scalar loop is already 20 µs over a realistic candidate set).

---

## Definition of Done (spec §10)

- [x] All four spikes + both ADV micro-opts measured; each ends adopt/defer/reject with a real number.
- [x] Reproducible benches (seed 1209, fixed corpus) under `scripts/perf/spikes/`; Nuitka = go/no-go notes.
- [x] Zero adopts → **no ADRs**; production stack (HTTP-JSON, Chroma, PyInstaller, FastAPI) unchanged.
- [x] No new dependency in `backend/requirements.txt` (msgpack/faiss-cpu installed ad-hoc into `.venv`,
      versions recorded above); no Rust; no shared-memory transport.
- [x] Speculative-plan Decision Ledger (§B) updated to match these verdicts.
