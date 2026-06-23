# Phase 12.6 — RAG Throughput (Collections, Batching, Background Ingest, Pruning)

**Track:** Velocity · **Depends on:** 12.0, 12.2 · **Branch:** `feat/phase-12-velocity-flywheel-multitenant`
**Status:** Planned · **Brief items:** RAG-001, RAG-002, RAG-004, Ollama rec #5

## 1. Context

`backend/rag/collections.py` defines **10** physical Chroma collections; the retriever loops them.
Embeddings are likely sent per-chunk. Ingestion blocks the request. Retrieved context isn't token-capped
before hitting the model, inflating prompt-processing time (TTFT).

## 2. Goals

- **Consolidate collections:** 10 → **1 (or 2)** physical collections, partitioned by a `doc_type`
  metadata field; queries use `where={"doc_type": ...}`. (Coordinate with 12.14: the consolidated
  collection also carries `tenant_id`.)
- **Batched embeddings:** send chunks to `nomic-embed-text` in arrays of 64–128, not one at a time.
- **Background ingestion:** `/ingest` returns `202 Accepted` + job id; pipeline runs via
  `BackgroundTasks`; progress streamed to the UI via SSE (reuse 12.4 plumbing).
- **Context pruning:** after rerank, cap retrieved context to a hard token budget (≤1500 tokens),
  dropping the tail. Uses the token counter from 12.5.

## 3. Non-goals (YAGNI)

- No FAISS/numpy replacement of Chroma (that's a 12.9 spike).
- No re-embedding of existing data beyond a one-time migration to the consolidated collection.
- Keep cosine/HNSW; only the physical partitioning changes.

## 4. Acceptance criteria

- [ ] `CollectionName` enum collapses to 1–2 names; `doc_type` metadata added on every write; retriever filters by `where`.
- [ ] A migration re-homes existing vectors into the consolidated collection (idempotent; documented).
- [ ] Embedder accepts a list and issues one HTTP call per batch of ≤128 (test asserts call count).
- [ ] `POST /ingest` returns 202 + job id immediately; progress events stream; final state queryable.
- [ ] Reranked context is truncated to ≤1500 tokens before prompt assembly (test on a long corpus).
- [ ] Ingestion bench (12.0): per-PDF time ≤ 3 s target; retrieval correctness unchanged (golden set).

## 5. Design

- `collections.py`: `DOCUMENTS = "acos_documents"` (single) + optional `EPHEMERAL`; `doc_type` enum
  retained as metadata. `chroma_client`/`indexer`/`retriever` take `doc_type` filter not collection name.
- `embedder.embed_batch(texts: list[str]) -> list[vector]`: chunk into ≤128, one POST each.
- Ingestion: `services/ingestion/pipeline.py` callable as a background task; `ingestion_failures`
  (Phase 11.1) reused for errors; a small `ingest_jobs` status (in-memory or `system_config`-backed;
  `# ponytail: in-memory job map is fine for single-process single-user`).
- Pruning: `services/rag/service.py` truncates post-rerank by cumulative token count.

## 6. File-level plan

```
EDIT backend/rag/collections.py          (consolidate; doc_type metadata)
EDIT backend/rag/chroma_client.py        (where-filter API)
EDIT backend/rag/indexer.py / retriever.py (doc_type instead of collection)
EDIT backend/rag/embedder.py             (embed_batch)
EDIT backend/services/rag/service.py     (token-capped context)
EDIT backend/api/v1/routes/ (ingest)     (202 + job id + SSE progress)
NEW  database/migrations/versions/<rev>_phase12_consolidate_collections.py
NEW  backend/tests/unit/test_embed_batch.py
NEW  backend/tests/unit/test_context_pruning.py
NEW  backend/tests/integration/test_background_ingest.py
NEW  backend/tests/integration/test_collection_filtering.py
```

## 7. Test plan (TDD)

- `test_embed_batch.py`: 300 chunks → 3 HTTP calls (≤128 each); order preserved.
- `test_context_pruning.py`: oversized rerank set → output ≤ budget, highest-ranked kept.
- `test_collection_filtering.py`: writes with mixed `doc_type` → `where` returns only the requested type.
- `test_background_ingest.py`: POST → 202 + job id; job reaches `done`; failure → `ingestion_failures`.

## 8. Plugin orchestration checklist

- [ ] `context7` — Chroma metadata filtering (`where`), Ollama embeddings batch endpoint, FastAPI BackgroundTasks.
- [ ] `superpowers:test-driven-development`.
- [ ] `security-guidance` — `/ingest` handles user files; path allowlist + size limits + no-exec still hold.

## 9. Perf budget impact

Big ingestion + TTFT win (fewer collections = less disk I/O; batching cuts embed round-trips; pruning
cuts prompt-eval). Run ingestion + TTFT benches.

## 10. Definition of Done

Consolidated collections + migration, batched embeddings, background ingest with progress, context
pruning, benches attached, golden-set retrieval unchanged, tests green.
