#!/usr/bin/env python
"""Ingest public GitHub repos for a user into the ACOS RAG knowledge base."""
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from backend.config import get_settings
from backend.database import SessionLocal
from backend.ingestion.entity_extractor import EntityExtractor
from backend.rag.chroma_client import ChromaManager
from backend.rag.embedder import Embedder
from backend.rag.indexer import RAGIndexer
from backend.services.knowledge_graph.service import KnowledgeGraphService
from backend.services.ollama_client import OllamaClient

logger = logging.getLogger(__name__)

_GH_API = "https://api.github.com"
_HEADERS = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}


def fetch_repos(username: str) -> list[dict]:
    resp = httpx.get(
        f"{_GH_API}/users/{username}/repos",
        params={"per_page": 100, "sort": "updated"},
        headers=_HEADERS,
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


def fetch_readme(username: str, repo: str, branch: str) -> str:
    url = f"https://raw.githubusercontent.com/{username}/{repo}/{branch}/README.md"
    try:
        resp = httpx.get(url, headers=_HEADERS, timeout=30)
        resp.raise_for_status()
        return resp.text
    except httpx.HTTPStatusError:
        return ""


def ingest(username: str) -> None:
    settings = get_settings()
    ollama = OllamaClient(base_url=settings.ollama_base_url)
    embedder = Embedder(ollama, model=settings.embedding_model)
    chroma = ChromaManager(path=settings.chroma_db_path)
    indexer = RAGIndexer(chroma, embedder)
    extractor = EntityExtractor(ollama if ollama.is_available() else None)

    repos = fetch_repos(username)
    logger.info("found %d repos for %s", len(repos), username)

    with SessionLocal() as session:
        kg_svc = KnowledgeGraphService(session)
        for repo in repos:
            name = repo["name"]
            description = repo.get("description") or ""
            language = repo.get("language") or ""
            branch = repo.get("default_branch", "main")
            readme = fetch_readme(username, name, branch)

            text = f"Repository: {name}\nLanguage: {language}\nDescription: {description}\n\n{readme}"
            doc_id = f"github_{username}_{name}"

            entities = extractor.extract(text, "github")
            metadata = {
                "repo_url": repo.get("html_url", ""),
                "language": language,
                "project_id": doc_id,
                "confidence_level": "strong_inference",
            }
            indexer.index_document("acos_github", doc_id, text[:2000], metadata)

            for skill in entities.get("skills", []):
                kg_svc.get_or_create_node(
                    "skill", skill["name"].lower(), skill["name"],
                    {"confidence": skill["confidence"], "source": "github"},
                )

            logger.info("indexed repo: %s", name)
        session.commit()


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    parser = argparse.ArgumentParser(description="Ingest GitHub repos into ACOS")
    parser.add_argument("--username", default="andrew-nguyen-9")
    args = parser.parse_args()
    ingest(args.username)


if __name__ == "__main__":
    main()
