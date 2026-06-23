# Model Setup Guide

ACOS uses [Ollama](https://ollama.ai) to run language models locally. All inference
happens on your machine. No API keys or cloud accounts are required.

---

## Required Models

| Model | Purpose | Approximate Size |
|-------|---------|-----------------|
| `qwen3:8b` | Text generation — resumes, cover letters, Q&A, copilot | ~5 GB |
| `nomic-embed-text` | Semantic embeddings for RAG retrieval | ~274 MB |

Both models must be available before ACOS can generate documents or answer
questions. The first-run wizard checks for them and reports any that are missing.

---

## Installation

### 1. Install Ollama

Download from https://ollama.ai or install via Homebrew:

```bash
brew install ollama
```

### 2. Start Ollama

```bash
ollama serve
```

Or open `Ollama.app` from your Applications folder. Ollama runs on
`http://localhost:11434` by default.

### 3. Pull the Required Models

```bash
ollama pull qwen3:8b
ollama pull nomic-embed-text
```

The `qwen3:8b` pull is approximately 5 GB. Allow 5–15 minutes depending on your
connection speed.

### 4. Verify

```bash
ollama list
```

Expected output includes at minimum:

```
NAME                  ID              SIZE      MODIFIED
qwen3:8b              ...             4.9 GB    ...
nomic-embed-text      ...             274 MB    ...
```

### 5. Confirm via ACOS

```bash
curl http://localhost:8000/api/v1/health/ollama | python3 -m json.tool
```

A healthy response looks like:

```json
{
  "ollama_available": true,
  "available_models": ["qwen3:8b", "nomic-embed-text"],
  "missing_models": []
}
```

If `missing_models` is non-empty, pull the listed models and re-check.

---

## Alternative Generation Models

You can use any Ollama-compatible chat model by updating the `default_model`
setting in ACOS. The embedding model (`nomic-embed-text`) should be left unchanged
unless you are prepared to re-index all collections.

| Model | Quality | Speed | Notes |
|-------|---------|-------|-------|
| `qwen3:8b` | ★★★★☆ | ★★★☆☆ | Default; best quality/speed balance |
| `llama3:8b` | ★★★☆☆ | ★★★★☆ | Faster; slightly lower output quality |
| `mistral:7b` | ★★★☆☆ | ★★★★☆ | Good for concise outputs |
| `qwen3:14b` | ★★★★★ | ★★☆☆☆ | Best quality; requires 12+ GB RAM |
| `qwen3:4b` | ★★★☆☆ | ★★★★★ | Fastest; use on 8 GB machines under pressure |

### Switching the Generation Model

1. Pull the model:
   ```bash
   ollama pull qwen3:14b
   ```

2. Update the ACOS setting:
   ```bash
   curl -X PUT http://localhost:8000/api/v1/settings/default_model \
     -H "Content-Type: application/json" \
     -d '{"value": "qwen3:14b"}'
   ```

3. Verify the change:
   ```bash
   curl http://localhost:8000/api/v1/settings | python3 -m json.tool
   ```

No restart is required. The new model is used on the next generation request.

---

## Switching the Embedding Model

Changing the embedding model invalidates all existing vector embeddings because
the new model produces vectors in a different space. You must re-index after
switching.

1. Pull the new embedding model:
   ```bash
   ollama pull mxbai-embed-large
   ```

2. Update the setting:
   ```bash
   curl -X PUT http://localhost:8000/api/v1/settings/embedding_model \
     -H "Content-Type: application/json" \
     -d '{"value": "mxbai-embed-large"}'
   ```

3. Re-index all collections:
   ```bash
   source .venv/bin/activate
   python scripts/maintenance/reindex_all.py
   ```

   This deletes and recreates all ChromaDB collections using the new model.
   Expect this to take several minutes for large document sets.

---

## Memory / TTFT Calibration (Phase 12.5)

On a 16GB M1, two models co-resident (generator + embedder) plus a large context
window can cross the swap cliff, collapsing throughput from ~20 t/s to <2 t/s.
ACOS calibrates the request payload automatically; two daemon-side settings are
yours to set because **ACOS does not launch the Ollama daemon** — the Tauri
sidecar launches the Python backend, not Ollama.

### Daemon environment (set these on your Ollama)

```bash
source scripts/setup_ollama.sh   # exports the vars + pulls pinned tags
```

| Env var | Value | Effect |
|---------|-------|--------|
| `OLLAMA_FLASH_ATTENTION` | `1` | Caps memory growth as context grows |
| `OLLAMA_KV_CACHE_TYPE` | `q8_0` | ~½ the KV-cache memory (requires flash attention) |

For the macOS `Ollama.app` daemon, persist via launchd then restart the app:

```bash
launchctl setenv OLLAMA_FLASH_ATTENTION 1
launchctl setenv OLLAMA_KV_CACHE_TYPE q8_0
```

These are read at daemon start — set them **before** `ollama serve`.

### What ACOS does in the request payload (no setup needed)

- **`num_ctx`** sized per operation, dynamically down to **2048** for short
  retrievals (a tiny chat shouldn't reserve 4096 of KV cache); capped at 4096.
- **`keep_alive: 1h`** holds the generator warm — no idle-unload cold start.
- **`num_thread: 4`** pins to the performance-core count.
- **Sequential unload:** after the query is embedded, the embedder is evicted
  (`keep_alive: 0`) *before* the generator runs, so the two never co-reside.

These are configurable via env: `ACOS_OLLAMA_NUM_THREAD`, `ACOS_OLLAMA_KEEP_ALIVE`.

### Pinned quantization

`scripts/setup_ollama.sh` pulls `qwen3:8b` (Q4_K_M) and `nomic-embed-text` so
every machine runs identical weights. Confirm with `ollama show qwen3:8b | grep -i quant`.

### Measuring it

```bash
OLLAMA_LIVE=1 python scripts/perf/ttft_bench.py --n 5
```

Reports two metrics: **first-chunk TTFT** (streaming-path latency, already near
the floor) and **visible-token TTFT under `think:false`** — the user-facing
latency 12.5 targets. With thinking enabled, qwen3 streams seconds of empty
"thinking" chunks before the first visible token; `think:false` collapses that.
Check `ollama ps` during a run to confirm only the generator is resident.

---

## Hardware Requirements

| RAM | Recommended Configuration |
|-----|--------------------------|
| 8 GB | `qwen3:4b` or `qwen3:8b` with memory pressure (usable but slow) |
| 16 GB | `qwen3:8b` — comfortable; generation takes 5–15 seconds |
| 32 GB | `qwen3:14b` — high quality; generation takes 10–30 seconds |
| 64 GB | `qwen3:32b` — maximum quality for complex resume generation |

### GPU Acceleration

Ollama uses Metal on Apple Silicon automatically. No configuration is needed.
Models load into GPU memory and inference is significantly faster than CPU-only.

To confirm GPU acceleration is active:

```bash
ollama ps
```

The `PROCESSOR` column should show `100% GPU` when a model is running.

---

## Checking Model Status

### Via Ollama directly

```bash
# List downloaded models
ollama list

# Check which models are currently loaded
ollama ps

# Pull a specific model
ollama pull <model-name>

# Remove a model to free disk space
ollama rm <model-name>
```

### Via ACOS health endpoint

```bash
curl http://localhost:8000/api/v1/health/ollama | python3 -m json.tool
```

### Via Ollama API

```bash
curl http://localhost:11434/api/tags | python3 -m json.tool
```

---

## Keeping Models Up to Date

Ollama does not auto-update models. To pull the latest version of a model:

```bash
ollama pull qwen3:8b
```

Re-pulling the same tag fetches the latest manifest and any updated layers.

---

## Troubleshooting

**Ollama not found after install**

Add Ollama to your PATH if the CLI is not found after a manual install:

```bash
export PATH="$HOME/.ollama/bin:$PATH"
```

**Model pulls fail halfway**

Disk space or network interruption. Check available space (`df -h ~`) and retry.
Ollama resumes interrupted pulls.

**Generation is very slow**

Check that GPU acceleration is active (`ollama ps`). If the PROCESSOR column shows
CPU only, restart Ollama and verify your machine has sufficient RAM to load the
model fully.

**ACOS still shows model as missing after pull**

The health check matches on the exact model name. Run `ollama list` and confirm
the name exactly matches what ACOS expects (e.g., `qwen3:8b` not `qwen3:8b-q4_0`).

---

## Packaged app (DMG)

Ollama is **not** bundled in the macOS DMG — it stays an external prerequisite. The
packaged app spawns only the Python sidecar and talks to your separately-installed Ollama
on `localhost`. The first-run wizard can download a missing model for you with progress
(Phase 13.7). See [`PACKAGING.md`](PACKAGING.md) for how the DMG is built, signed, and
verified, and for the single signed auto-update channel (ADR-011).

---

## See Also

- [User Guide](USER_GUIDE.md) — end-to-end usage walkthrough
- [Troubleshooting](TROUBLESHOOTING.md) — common issues and fixes
- [Packaging](PACKAGING.md) — DMG build, signing, external-Ollama contract, auto-update
- [Data Import Guide](DATA_IMPORT.md) — populating the knowledge graph
