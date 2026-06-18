# ADR-004: Ollama + Qwen3 8B as Local LLM Provider

**Status:** Accepted  
**Date:** 2026-06-18  
**Deciders:** Andrew Nguyen

---

## Context

Local LLM inference is required (see ADR-001). The system needs a model that:
- Runs on consumer hardware (MacBook Pro with Apple Silicon)
- Handles structured generation (JSON output)
- Handles English-language writing tasks (resume, cover letter)
- Is available without API keys

---

## Decision

Use **Ollama** as the local model server and **Qwen3 8B** as the default model.
Embedding model: **nomic-embed-text** (also via Ollama).

---

## Consequences

**Positive:**
- Ollama is the de facto standard for local LLM serving on macOS
- Qwen3 8B has strong structured output and instruction-following
- Metal GPU acceleration on Apple Silicon
- Ollama handles model download, quantization, and serving
- REST API compatible with OpenAI client format (easy to swap models)
- `nomic-embed-text` is lightweight (≈274M params) and produces high-quality 768-dim embeddings

**Negative:**
- Qwen3 8B is below frontier model capability (GPT-4o, Claude Sonnet)
- Generation slower than cloud APIs (~5–15 tokens/sec vs ~80 tokens/sec)
- Model quality caps resume bullet rewriting quality

**Mitigations:**
- Knowledge graph grounding compensates for model quality (model assembles from real evidence)
- System config allows swapping to larger models (Qwen3 14B, Mistral, etc.)
- Prompts designed to minimize creative generation; maximize evidence assembly

---

## Model Configuration

| Parameter | Value |
|-----------|-------|
| Default model | `qwen3:8b` |
| Embedding model | `nomic-embed-text` |
| Temperature (generation) | 0.3 |
| Temperature (analysis) | 0.1 |
| Context window | 8192 tokens |
| Ollama endpoint | `http://localhost:11434` |

---

## Alternatives Considered

| Alternative | Why Rejected |
|-------------|-------------|
| LLaMA 3.1 8B | Qwen3 8B shows stronger structured output in benchmarks |
| Mistral 7B | Similar quality; Qwen3 has better multilingual (not needed but not a cost) |
| Gemma 2 9B | Less community tooling for structured generation |
| Phi-3.5 Mini | Smaller; quality insufficient for cover letter generation |
| GPT-4o (cloud) | Violates local-first and privacy requirements |
