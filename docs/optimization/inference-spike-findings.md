# Phase 12.8 — Advanced Inference Spikes: Findings

**Date:** 2026-06-22 · **Branch:** `feat/phase-12-velocity-flywheel-multitenant`
**Ollama:** 0.30.10 · **Model:** qwen3:8b (16GB M1) · **Spec:** `docs/v1/plans/2026-06-22-phase-12-8-inference-spikes.md`

This doc records **all three** spike outcomes regardless of accept/reject (spec §6, §10).
Each spike was gated by a `context7` viability check **before** any code (the laziness ladder
rung 1: "does this need to exist?"). Two of three were no-gos on the Ollama API surface.

| Spike | Viability (context7 + live daemon) | Verdict | Code shipped |
|-------|-----------------------------------|---------|--------------|
| A — structured output | `format` = JSON Schema, supported | **ACCEPT** | flag + client param + 4 routes + bench |
| B — negative logit bias | not exposed by Ollama `options` | **NO-GO** | none |
| C — speculative decoding | exists at ops layer only, not `/api/generate` | **NO-GO (defer 12.9)** | none |

---

## Spike A — Structured output (constrained JSON decoding) → **ACCEPTED**

### Spec correction: it is `format`, not GBNF

The spec (§5) said "pass a GBNF grammar to Ollama" + "`backend/prompts/grammars/*.gbnf`".
**That is wrong for Ollama 0.30.10.** Ollama does not take raw `.gbnf` files over `/api/generate`.
It exposes structured output via a **top-level `format` parameter** that accepts either `"json"`
or a **JSON-Schema object** (structured-outputs landed ~Ollama 0.5; confirmed via `context7` against
`/ollama/ollama` `docs/capabilities/structured-outputs.mdx` + `docs/api.md`).

Consequences:
- **No grammar files.** Schemas are Python `dict` literals next to each route (no new file I/O →
  no path-traversal surface → no security review burden, vs. loading `.gbnf` from disk).
- **Flag renamed** `ENABLE_GBNF` → `ACOS_ENABLE_STRUCTURED_OUTPUT` (`Settings.enable_structured_output`,
  default **off**). The spec's flag name described a mechanism Ollama doesn't have.
- **Test file** `test_structured_output.py` (not `test_gbnf_json.py`) for the same reason.

### What shipped
- `ollama_client.generate()` / `generate_stream()`: new `output_format: dict | None` → top-level
  `format` payload key, threaded **into both** methods like 12.5's `think` (spec trap 6). Streaming
  has no JSON caller today (copilot stream is prose) — added for path symmetry, `ponytail:`-marked.
- 4 JSON-extraction routes wired behind the flag, each pairing `format=<schema>` with `think=False`
  (spec trap 4 — a qwen3 `<think>` block would violate the schema constraint; extraction needs no
  reasoning anyway). Flag off → `output_format=None`, `think=None` → **byte-identical** to today.
  - `entity_extractor.py` `_EXTRACT_SCHEMA` (skills/experiences/projects arrays)
  - `ats/scorer.py` `_ATS_SCHEMA` (scores + keyword arrays)
  - `questions/generator.py` `_QUESTIONS_SCHEMA` (top-level array) + `_ANSWER_SCHEMA`
- Schemas are **structure-only** (required keys are the container shape; item fields stay open) so the
  model never invents required fields — no-hallucination intact; confidence still traces to evidence.

### Honest framing of the win (spec traps 4 + 5)
The win is **correctness, not latency**: parse-error → 0, retry/fallback → 0. Structured output does
**not** shorten TTFT — prompt-eval / reasoning time dominates (12.5/12.6), and `format` doesn't touch
it. It also eliminates the `json.loads` failure path but does **not** remove the 120s-timeout→regex
fallback (12.6) that reasoning-time can still trigger — though pairing with `think=False` collapses
that reasoning time on these routes (see baseline timeouts below).

### Bench: `scripts/perf/structured_output_bench.py` (OLLAMA_LIVE=1, live qwen3:8b)

Two arms over N varied resume snippets through the entity-extraction prompt; counts raw-response
JSON validity. Baseline = flag off (production today: no `format`, reasoning on). Structured = flag on
(`format` + `think:false`). A timeout counts as a failure (the route falls back).

**Live run, n=12, qwen3:8b, macOS-arm64 (`scripts/perf/baselines/structured_output.json`):**

| Arm | valid JSON | parse-errors | timeouts | failures |
|-----|-----------:|-------------:|---------:|---------:|
| baseline (flag **off**) | **2 / 12** | 0 | 10 | **10** |
| structured (flag **on**) | **12 / 12** | 0 | 0 | **0** |

Retry/fallback count: **10 → 0**. Valid-JSON rate: **17% → 100%**.

Read this honestly: the baseline failures are **timeouts**, not `json.loads` errors — with reasoning
on, extraction blows past the 120s client timeout (the 12.6 timeout→regex fallback path), so most
calls never returned anything to parse. The two baseline calls that *did* finish in time happened to
parse. The flag's win is therefore the **combination** it enables: `think=False` removes the
reasoning-time timeouts on these routes, and `format` guarantees the survivors are valid JSON. Both
are off by default and toggle together via the one flag. The headline "0 parse-errors" claim holds
on the structured arm; the dramatic failure drop is dominated by killing reasoning timeouts.

**Accept gate:** structured arm at 100% valid / 0 failures while the baseline shows failures. ✅ (see
numbers above). Harness supports the full `--n 50`; the recorded run uses a smaller N because the
reasoning-on baseline arm times out per call (≤120s each), which is itself the failure being fixed.

---

## Spike B — Negative logit bias → **NO-GO (not exposed by Ollama)**

`context7` (`/ollama/ollama` `api/types.go` `Options` struct, the authoritative option list) +
live `ollama` 0.30.10: the `/api/generate` `options` object supports
`num_keep, seed, num_predict, top_k, top_p, min_p, typical_p, repeat_last_n, temperature,
repeat_penalty, presence_penalty, frequency_penalty, stop` — **no `logit_bias`**.

`logit_bias` is a llama.cpp-server / OpenAI-API feature Ollama does not surface on its native
`/api/generate`. The closest available knobs are `presence_penalty` / `frequency_penalty` (global,
not per-token) and `stop` (ends generation, doesn't suppress a preamble) — none implement the
"ban specific filler token ids" the spike specified.

**Decision:** no code. Building a `logit_bias` path Ollama silently ignores would be worse than
nothing. Revisit only if/when the stack moves to raw llama.cpp bindings — that is a **12.9**
architecture decision, explicitly out of scope here (spec §3 non-goal). The filler-preamble token
saving the spike targeted is better addressed at the **prompt** level (already done: stable
fixed-prefix RAG instructions, 12.5) than at the decoder.

---

## Spike C — Speculative / draft decoding → **NO-GO for application code (defer to 12.9)**

The machinery **exists** in Ollama 0.30.10:
- `options.draft_num_predict` (default 4, 0 to disable) — max speculative draft tokens per step
  "when a draft model is available" (`context7` `docs/modelfile.mdx`).
- `ollama create --draft-quantize <level>` — a CLI flag to quantize an attached draft model.

But it is **not reachable from `/api/generate`** the way the spike assumed (a tiny draft model
drafting for the 8B at request time):
- A draft model is attached at **model-build time** via `ollama create` (an ops/Modelfile concern),
  not as a per-request API parameter. There is **no application code** in this stack (`ollama_client.py`
  speaks `/api/generate`) that could turn it on — it would belong in `scripts/setup_ollama.sh` /
  `MODEL_SETUP.md`, like the 12.5 KV-cache-quant trap, not in Python.
- **qwen3:8b is a reasoning model** (12.5 finding). Speculative decoding's speedup scales with draft
  **accept-rate**; high-entropy reasoning tokens accept poorly, so the expected win on our actual
  workload is small and unproven.
- Producing a tokens/sec number would require building a draft-fused qwen3 variant (pull a
  vocab-compatible draft model + `ollama create` with a draft) — i.e. escalating into model packaging,
  which the spec's non-goals forbid in 12.8 (§3: "No switch to raw llama.cpp … escalates to a 12.9
  architecture decision").

**Decision:** no code, no bench. Go/no-go = **defer to 12.9** (architecture spikes), where a custom
fused-model build can be evaluated as an ops change with its own budget case. Recorded recipe for that
future work: pull a small vocab-compatible draft (e.g. a `qwen3` 0.6b-class model), `ollama create
qwen3-spec` with the draft attached + `--draft-quantize q8_0`, then A/B tokens/sec vs plain qwen3:8b
via `scripts/perf/ttft_bench.py`.

---

## Definition of Done (spec §10)

- [x] All three spikes evaluated with a viability verdict; A benched with live numbers.
- [x] Accepted spike (A) ships behind a default-off flag, with tests and a bench delta.
- [x] Rejected spikes (B, C) leave a findings entry only — **no force-merged code**.
- [x] No new dependency; no llama.cpp bindings; no grammar for prose routes.
