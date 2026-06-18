# ADR-003: ChromaDB for Vector Storage and Semantic Search

**Status:** Accepted  
**Date:** 2026-06-18  
**Deciders:** Andrew Nguyen

---

## Context

The RAG pipeline requires a vector database to store embeddings of career documents and
retrieve semantically relevant content for generation. Options include ChromaDB, Qdrant,
Weaviate, FAISS, and SQLite with vector extensions (sqlite-vss).

---

## Decision

Use ChromaDB as the vector store, configured with `PersistentClient` (local disk storage).

---

## Consequences

**Positive:**
- Pure Python; no server required; runs in-process
- Persistent on disk out of the box
- Excellent Python API; well-documented
- Supports metadata filtering alongside vector search
- Collection-per-entity model maps cleanly to ACOS design (10 collections)
- Active development and large community

**Negative:**
- Performance ceiling lower than dedicated vector DBs (Qdrant, Weaviate)
- Not suitable for >1M vectors (not a concern for single-user career data)
- No built-in BM25; hybrid search requires manual implementation

**Mitigations:**
- Career data volume will never approach ChromaDB's limits
- BM25 reranking implemented manually in `backend/rag/reranker.py`

---

## Alternatives Considered

| Alternative | Why Rejected |
|-------------|-------------|
| Qdrant | Requires running a separate server process |
| Weaviate | Same; server-based |
| FAISS | No metadata filtering; requires custom persistence layer |
| sqlite-vss | Experimental; limited Python support; couples vector search to SQLite |
| pgvector | Requires PostgreSQL |
