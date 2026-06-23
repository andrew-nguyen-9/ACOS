# Phase 12.5 — Ollama Memory / TTFT Calibration

**Track:** Velocity · **Depends on:** 12.0, 12.4 · **Branch:** `feat/phase-12-velocity-flywheel-multitenant`
**Status:** Planned · **Brief items:** LLM-002, LLM-004, Ollama recs #1,2,6,8,9,10

> Tuning, not architecture. All changes are `options` payload + env vars + prompt ordering.
> Target: 16GB M1 — avoid the swap cliff (20 t/s → <2 t/s) described in the brief.

## 1. Context

`ollama_client` sends only `temperature`/`num_predict`. No `num_ctx`, `keep_alive`, `num_thread`; no
KV-cache quantization; no sequential model unload; system prompts aren't guaranteed byte-identical
across calls (defeats Ollama prefix caching).

## 2. Goals (each independently shippable & measured)

- **num_ctx calibration:** per-operation context cap (cover letter 4096, dynamic down to 2048 when
  retrieved tokens are small). Count tokens before the call.
- **keep_alive:** `"1h"` for the generator to avoid idle unload cold starts.
- **Sequential model unload:** after embedding, fire-and-forget `keep_alive: 0` for `nomic-embed-text`
  before invoking `qwen3` (prevents 16GB starvation).
- **num_thread:** pin to performance-core count (default 4; configurable).
- **KV-cache quant + flash attention:** set `OLLAMA_KV_CACHE_TYPE=q8_0` + flash-attn env when the
  Rust sidecar launches the Ollama daemon.
- **Prompt prefix preservation:** system prompt + fixed instructions byte-identical and first;
  dynamic RAG context last → Ollama reuses the system-prompt KV cache.
- **Quantization standardization:** sidecar setup pulls an explicit `Q4_K_M`/`Q5_K_M` tag.

## 3. Non-goals (YAGNI)

- No model-router / multi-model orchestration.
- No per-token logit bias here (that's a 12.8 spike).
- `num_thread`/quant tag are config with sane defaults — not auto-detected hardware probing (`# ponytail: default 4 P-cores, expose a setting; auto-detect only if users vary`).

## 4. Acceptance criteria

- [ ] Generation payloads include calibrated `num_ctx`, `keep_alive`, `num_thread` (asserted in client test).
- [ ] A fast token counter (e.g. `tiktoken` cl100k or local tokenizer) sizes `num_ctx`; test covers the down-scale-to-2048 path.
- [ ] Embedder receives `keep_alive: 0` after a batch; generator call follows (ordering test).
- [ ] Prompt builder emits a byte-identical fixed prefix across two calls with different RAG context (test diffs the prefix region).
- [ ] Sidecar sets KV-cache + flash-attn env and pulls the pinned quant tag (documented + script).
- [ ] TTFT bench (12.0) improves vs 12.4 baseline; memory stays under the swap threshold (manual `ollama ps` note in PR).

## 5. Design

- `ollama_client`: `options` builder takes an `Operation` enum → `num_ctx`/`num_thread`; add
  `keep_alive`. New `unload(model)` helper.
- `prompt_loader` / prompt builders: enforce `[FIXED SYSTEM PREFIX][FIXED INSTRUCTIONS][DYNAMIC CONTEXT]`
  ordering; add a test asserting prefix stability.
- Token counting: `backend/services/tokens.py` thin wrapper (`# ponytail: tiktoken approximation is fine for budgeting, not exact for qwen`).
- Sidecar (`frontend/src-tauri/src/`): set `OLLAMA_KV_CACHE_TYPE`, flash-attn env before spawning Ollama;
  setup script pulls explicit quant tag.

## 6. File-level plan

```
EDIT backend/services/ollama_client.py        (num_ctx/keep_alive/num_thread/unload)
NEW  backend/services/tokens.py               (fast token counter)
EDIT backend/services/prompt_loader.py + prompt builders (prefix ordering)
EDIT backend/services/rag/service.py          (unload embedder before generate)
EDIT frontend/src-tauri/src/*.rs              (Ollama env vars on launch)
EDIT scripts/ (sidecar/model setup)           (pin Q4_K_M/Q5_K_M tag)
NEW  backend/tests/unit/test_ollama_options.py
NEW  backend/tests/unit/test_prompt_prefix_stability.py
```

## 7. Test plan (TDD)

- `test_ollama_options.py`: each operation → expected options; dynamic num_ctx scaling; embedder unload ordering.
- `test_prompt_prefix_stability.py`: two builds with different context share an identical prefix prefix-region.

## 8. Plugin orchestration checklist

- [ ] `context7` — Ollama `options` (num_ctx/keep_alive/num_thread), `OLLAMA_KV_CACHE_TYPE`, flash attention, model tags.
- [ ] `superpowers:test-driven-development` + `verification-before-completion` (TTFT/memory numbers must be real).

## 9. Perf budget impact

Directly targets TTFT and prevents swap. No bundle impact. Record TTFT + `ollama ps` memory before/after.

## 10. Definition of Done

Calibrated options, sequential unload, stable prefix, KV-quant/flash-attn env, pinned quant, TTFT bench + memory note, tests green.
