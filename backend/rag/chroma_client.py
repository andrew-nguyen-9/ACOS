import logging
import threading
from typing import TYPE_CHECKING, Any

from backend.rag.collections import COLLECTION_CONFIGS, ALL_COLLECTION_NAMES

if TYPE_CHECKING:
    from chromadb import Collection

logger = logging.getLogger(__name__)

# ponytail: module-level memo, not a DI container. One PersistentClient per
# process — routes build a fresh ChromaManager per request otherwise, paying the
# client construction each time. Re-keyed on path so a test pointing at a new
# tmpdir gets its own client instead of a stale one.
_manager: "ChromaManager | None" = None


def get_chroma_manager(path: str) -> "ChromaManager":
    """Process-wide memoized ChromaManager. chromadb stays lazy until first use.

    The memo itself is not locked — a construction race just rebuilds a cheap,
    side-effect-free ``ChromaManager`` (the expensive ``PersistentClient`` is
    built lazily under ``_client_lock``, so no client leaks). workers=1 makes a
    race unlikely anyway.
    """
    global _manager
    if _manager is None or _manager._path != path:
        _manager = ChromaManager(path)
    return _manager


def reset_chroma_manager() -> None:
    """Drop the memoized manager. Tests reset it per-function for isolation."""
    global _manager
    _manager = None


def _compose_tenant_where(
    where: "dict[str, Any] | None", tenant_id: str | None
) -> "dict[str, Any] | None":
    """AND a tenant predicate into an existing metadata `where` (12.14 isolation).

    Composes with the 12.6 doc_type filter rather than replacing it; Chroma needs an
    explicit ``$and`` to combine two metadata predicates.
    """
    if tenant_id is None:
        return where
    tenant_clause = {"tenant_id": tenant_id}
    if not where:
        return tenant_clause
    return {"$and": [tenant_clause, where]}


class ChromaManager:
    def __init__(self, path: str) -> None:
        self._path = path
        self._client_obj = None  # lazy: built on first use (defers chromadb import)
        self._client_lock = threading.Lock()

    @property
    def _client(self):
        # ponytail: lazy import keeps chromadb (+numpy/onnxruntime/otel) off the
        # startup path; only callers that touch a collection pay the import cost.
        # Double-checked lock: steady state skips the lock; first use is race-safe
        # if a manager is ever shared across threads.
        if self._client_obj is None:
            with self._client_lock:
                if self._client_obj is None:
                    import chromadb

                    self._client_obj = chromadb.PersistentClient(path=self._path)
        return self._client_obj

    def get_or_create_collection(self, name: str) -> "Collection":
        metadata = COLLECTION_CONFIGS.get(name, {"hnsw:space": "cosine"})
        return self._client.get_or_create_collection(name=name, metadata=metadata)

    def init_all_collections(self) -> None:
        """Idempotently create the consolidated ACOS collection(s) (12.6: one)."""
        for name in ALL_COLLECTION_NAMES:
            self.get_or_create_collection(name)
        logger.info("ChromaDB: %d collection(s) ready", len(ALL_COLLECTION_NAMES))

    def add(
        self,
        collection: str,
        ids: list[str],
        documents: list[str],
        embeddings: list[list[float]],
        metadatas: list[dict[str, Any]],
        tenant_id: str | None = None,
    ) -> None:
        if tenant_id is not None:
            metadatas = [{**m, "tenant_id": tenant_id} for m in metadatas]
        col = self.get_or_create_collection(collection)
        col.add(ids=ids, documents=documents, embeddings=embeddings, metadatas=metadatas)

    def upsert(
        self,
        collection: str,
        ids: list[str],
        documents: list[str],
        embeddings: list[list[float]],
        metadatas: list[dict[str, Any]],
        tenant_id: str | None = None,
    ) -> None:
        if tenant_id is not None:
            metadatas = [{**m, "tenant_id": tenant_id} for m in metadatas]
        col = self.get_or_create_collection(collection)
        col.upsert(ids=ids, documents=documents, embeddings=embeddings, metadatas=metadatas)

    def query(
        self,
        collection: str,
        query_embeddings: list[list[float]],
        n_results: int = 10,
        where: dict[str, Any] | None = None,
        tenant_id: str | None = None,
    ) -> dict[str, Any]:
        col = self.get_or_create_collection(collection)
        kwargs: dict[str, Any] = {
            "query_embeddings": query_embeddings,
            "n_results": n_results,
        }
        where = _compose_tenant_where(where, tenant_id)
        if where:
            kwargs["where"] = where
        return col.query(**kwargs)

    def list_collection_names(self) -> list[str]:
        """Names of collections that physically exist (does not create any)."""
        return [c.name for c in self._client.list_collections()]

    def export_all(self, collection: str) -> dict[str, Any]:
        """All records in a collection, embeddings included (for the 12.6 migration)."""
        col = self.get_or_create_collection(collection)
        return dict(col.get(include=["documents", "embeddings", "metadatas"]))

    def delete_collection(self, name: str) -> None:
        self._client.delete_collection(name=name)

    def get(self, collection: str, ids: list[str]) -> dict[str, Any]:
        # Default include returns ids + metadatas + documents (enough for the
        # content_hash skip-unchanged check); avoids the Include enum typing.
        col = self.get_or_create_collection(collection)
        return dict(col.get(ids=ids))

    def delete(self, collection: str, ids: list[str]) -> None:
        col = self.get_or_create_collection(collection)
        col.delete(ids=ids)

    def count(self, collection: str) -> int:
        col = self.get_or_create_collection(collection)
        return col.count()

    def health_check(self) -> bool:
        try:
            self._client.heartbeat()
            return True
        except Exception:
            return False
