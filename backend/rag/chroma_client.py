import logging
import threading
from typing import TYPE_CHECKING, Any

from backend.rag.collections import COLLECTION_CONFIGS, ALL_COLLECTION_NAMES

if TYPE_CHECKING:
    from chromadb import Collection

logger = logging.getLogger(__name__)


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
        """Idempotently create all 10 ACOS collections."""
        for name in ALL_COLLECTION_NAMES:
            self.get_or_create_collection(name)
        logger.info("ChromaDB: all %d collections ready", len(ALL_COLLECTION_NAMES))

    def add(
        self,
        collection: str,
        ids: list[str],
        documents: list[str],
        embeddings: list[list[float]],
        metadatas: list[dict[str, Any]],
    ) -> None:
        col = self.get_or_create_collection(collection)
        col.add(ids=ids, documents=documents, embeddings=embeddings, metadatas=metadatas)

    def upsert(
        self,
        collection: str,
        ids: list[str],
        documents: list[str],
        embeddings: list[list[float]],
        metadatas: list[dict[str, Any]],
    ) -> None:
        col = self.get_or_create_collection(collection)
        col.upsert(ids=ids, documents=documents, embeddings=embeddings, metadatas=metadatas)

    def query(
        self,
        collection: str,
        query_embeddings: list[list[float]],
        n_results: int = 10,
        where: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        col = self.get_or_create_collection(collection)
        kwargs: dict[str, Any] = {
            "query_embeddings": query_embeddings,
            "n_results": n_results,
        }
        if where:
            kwargs["where"] = where
        return col.query(**kwargs)

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
