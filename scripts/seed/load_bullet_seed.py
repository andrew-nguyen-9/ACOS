"""
Load bullet_training_data.py into ChromaDB acos_bullet_examples collection.
Idempotent: skips any bullet whose SHA-256 already exists in the collection.

Usage:
    python scripts/seed/load_bullet_seed.py [--dry-run] [--batch-size N]
"""

import argparse
import hashlib
import sys
import time
from pathlib import Path

# Allow running from repo root
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.seed.bullet_training_data import BULLET_EXAMPLES
from scripts.seed.bullet_training_data_extended import BULLET_EXAMPLES_EXTENDED

_ALL_BULLETS = BULLET_EXAMPLES + BULLET_EXAMPLES_EXTENDED

CHROMA_PATH = Path("database/chroma")
COLLECTION_NAME = "acos_bullet_examples"
OLLAMA_MODEL = "nomic-embed-text"
DEFAULT_BATCH = 50


def sha256(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def embed_batch(texts: list[str]) -> list[list[float]]:
    import ollama  # type: ignore[import]
    return [ollama.embeddings(model=OLLAMA_MODEL, prompt=t)["embedding"] for t in texts]


def load(dry_run: bool = False, batch_size: int = DEFAULT_BATCH) -> None:
    import chromadb  # type: ignore[import]

    client = chromadb.PersistentClient(path=str(CHROMA_PATH))
    col = client.get_or_create_collection(COLLECTION_NAME)

    existing_ids: set[str] = set(col.get(include=[])["ids"])
    bullets_to_add = [b for b in _ALL_BULLETS if sha256(b["text"]) not in existing_ids]

    print(f"Total bullets : {len(_ALL_BULLETS)}")
    print(f"Already loaded: {len(existing_ids)}")
    print(f"To add        : {len(bullets_to_add)}")

    if dry_run:
        print("[dry-run] Skipping writes.")
        return

    added = 0
    for i in range(0, len(bullets_to_add), batch_size):
        batch = bullets_to_add[i : i + batch_size]
        texts = [b["text"] for b in batch]
        ids = [sha256(t) for t in texts]
        metadatas = [
            {
                "role_type": b["role_type"],
                "dimension": b["dimension"],
                "verb": b["verb"],
                "has_metric": str(b["has_metric"]).lower(),
            }
            for b in batch
        ]
        embeddings = embed_batch(texts)
        col.add(ids=ids, embeddings=embeddings, documents=texts, metadatas=metadatas)
        added += len(batch)
        print(f"  Added {added}/{len(bullets_to_add)}", end="\r", flush=True)
        time.sleep(0.1)  # ponytail: gentle rate-limit for local Ollama

    print(f"\nDone. {added} bullets added to '{COLLECTION_NAME}'.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed bullet training data into ChromaDB.")
    parser.add_argument("--dry-run", action="store_true", help="Preview without writing")
    parser.add_argument("--batch-size", type=int, default=DEFAULT_BATCH)
    args = parser.parse_args()
    load(dry_run=args.dry_run, batch_size=args.batch_size)
