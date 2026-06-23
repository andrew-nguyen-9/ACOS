# Phase 12.7 — FTS5 Lexical Search (Replace Python BM25)

**Track:** Velocity · **Depends on:** 12.2, 12.6 · **Branch:** `feat/phase-12-velocity-flywheel-multitenant`
**Status:** Planned · **Brief items:** RAG-003

## 1. Context

Hybrid retrieval uses a Python BM25 layer (`rank_bm25`-style) over the corpus, which is slow and
duplicates content in Python memory. SQLite ships **FTS5** with native BM25 ranking — no new
dependency, runs in the DB next to the data. The Phase 11.1 fallback already proposed FTS5.

## 2. Goals

- Add an **FTS5 virtual table** mirroring document/experience text, kept in sync via triggers.
- Replace the Python BM25 lexical leg of hybrid retrieval with `SELECT ... WHERE fts MATCH ? ORDER BY rank`.
- Keep the existing reranker fusing dense (Chroma) + lexical (FTS5) results.

## 3. Non-goals (YAGNI)

- No `tantivy-py` / external search engine (FTS5 covers it natively — Ponytail rung 3).
- No change to dense retrieval or reranking math; only the lexical source swaps.

## 4. Acceptance criteria

- [ ] FTS5 table created by migration; triggers keep it in sync on insert/update/delete.
- [ ] Lexical search returns BM25-ranked results via FTS5; old Python BM25 code removed.
- [ ] Hybrid retrieval golden set: results equal-or-better vs the Python BM25 baseline (documented comparison).
- [ ] Lexical query latency improves (bench); memory footprint drops (no in-Python corpus).
- [ ] `rank_bm25` (or equivalent) dependency removed from `pyproject.toml`.

## 5. Design

- Migration: `CREATE VIRTUAL TABLE documents_fts USING fts5(content, doc_id UNINDEXED, tenant_id UNINDEXED, content='...');`
  + AFTER INSERT/UPDATE/DELETE triggers on the source table.
- `backend/services/rag/lexical.py`: `search(query, tenant_id, k)` → FTS5 MATCH + `bm25()` rank.
- Retriever/reranker: dense + `lexical.search` fused as before.
- `tenant_id` column is forward-compat with 12.14 (nullable until tenants land; `# ponytail: nullable now, NOT NULL after 12.14 migration`).

## 6. File-level plan

```
NEW  database/migrations/versions/<rev>_phase12_fts5.py
NEW  backend/services/rag/lexical.py
EDIT backend/services/rag/service.py / retriever  (use FTS5 lexical leg)
DEL  python BM25 module + dependency
NEW  backend/tests/unit/test_fts5_lexical.py
EDIT backend/tests/ (hybrid retrieval golden comparison)
```

## 7. Test plan (TDD)

- `test_fts5_lexical.py`: seed rows → MATCH returns expected ranked ids; trigger sync on update/delete.
- Golden comparison test: hybrid scores vs recorded Python-BM25 baseline within tolerance or better.

## 8. Plugin orchestration checklist

- [ ] `context7` — SQLite FTS5 (`bm25()`, external-content tables, triggers).
- [ ] `superpowers:test-driven-development`.

## 9. Perf budget impact

Faster lexical leg, lower memory. Verify FTS5 is compiled into the bundled SQLite (PyInstaller). Bench retrieval.

## 10. Definition of Done

FTS5 table + triggers, lexical leg swapped, Python BM25 removed, golden set equal-or-better, bench attached, tests green.
