"""Document-ingestion throughput benchmark against live Ollama.

Runs the real `IngestionPipeline` (parse → entity extract → chunk → embed →
index) on a sample PDF and times it end-to-end. Reports per-document seconds.
The embedding + entity-extraction steps hit Ollama, so this is opt-in:

    OLLAMA_LIVE=1 python scripts/perf/ingest_bench.py
    OLLAMA_LIVE=1 python scripts/perf/ingest_bench.py --pdf path/to.pdf --n 3

With OLLAMA_LIVE unset it prints "skipped" and exits 0. If no sample PDF is
found it also skips cleanly (the repo's sample resumes live in
`.static_files/` which is gitignored, so the path is configurable).

Uses a throwaway in-memory SQLite DB and a temp Chroma dir — never touches the
real database (measurement only, per Phase 12.0 non-goals).
"""
from __future__ import annotations

import argparse
import json
import os
import platform
import statistics
import sys
import tempfile
import time
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

_DEFAULT_OUT = Path(__file__).parent / "baselines" / "ingest.json"

# ponytail: default to a repo sample resume; overridable with --pdf. Skips if absent.
_DEFAULT_PDFS = [
    Path(".static_files/resumes/Andrew-Nguyen_Resume.pdf"),
    Path("mock-designs/resume-examples/devin-jones-resume-sample_accessible.pdf"),
]


def _live() -> bool:
    return bool(os.environ.get("OLLAMA_LIVE"))


def _find_pdf(explicit: Path | None) -> Path | None:
    if explicit is not None:
        return explicit if explicit.is_file() else None
    root = Path(__file__).resolve().parents[2]
    for rel in _DEFAULT_PDFS:
        if (root / rel).is_file():
            return root / rel
    return None


def run(
    pdf: Path, n: int = 3, out_path: Path | None = _DEFAULT_OUT, regex_extract: bool = False
) -> dict | None:
    """Time end-to-end ingestion. ``regex_extract`` skips the LLM entity-extraction
    call (regex fallback) to isolate the parse→embed→index cost that 12.6 affects;
    the full pipeline's time is otherwise dominated by the qwen3 extraction call."""
    from sqlalchemy import create_engine, event
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import StaticPool

    import backend.models  # noqa: F401 — registers models
    from backend.config import get_settings
    from backend.ingestion.entity_extractor import EntityExtractor
    from backend.ingestion.pipeline import IngestionPipeline
    from backend.models.base import Base
    from backend.rag.chroma_client import ChromaManager
    from backend.rag.embedder import Embedder
    from backend.rag.indexer import RAGIndexer
    from backend.services.knowledge_graph.service import KnowledgeGraphService
    from backend.services.ollama_client import OllamaClient

    settings = get_settings()
    ollama = OllamaClient(base_url=settings.ollama_base_url)
    if not ollama.is_available():
        print(f"skipped: Ollama not reachable at {settings.ollama_base_url}")
        return None

    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    event.listen(
        engine, "connect",
        lambda c, _: c.cursor().execute("PRAGMA foreign_keys=ON"),
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, autocommit=False, autoflush=False)

    samples = []
    with tempfile.TemporaryDirectory() as chroma_dir:
        embedder = Embedder(ollama, model=settings.embedding_model)
        chroma = ChromaManager(path=chroma_dir)
        indexer = RAGIndexer(chroma, embedder)
        # regex_extract=True passes no Ollama client → regex-only extraction, so the
        # measured time reflects parse+embed+index (the 12.6 surface), not LLM reasoning.
        extractor = EntityExtractor(None if regex_extract else ollama)
        for _ in range(n):
            session = Session()
            kg_svc = KnowledgeGraphService(session)
            pipeline = IngestionPipeline(
                session=session,
                kg_service=kg_svc,
                indexer=indexer,
                entity_extractor=extractor,
                allowed_dirs=[str(pdf.parent)],
            )
            t0 = time.perf_counter()
            pipeline.ingest(str(pdf))
            samples.append(time.perf_counter() - t0)
            session.rollback()
            session.close()
    engine.dispose()

    result = {
        "metric": "ingest_seconds_per_doc",
        "date": date.today().isoformat(),
        "pdf": str(pdf.name),
        "n": n,
        "median_s": round(statistics.median(samples), 3),
        "min_s": round(min(samples), 3),
        "max_s": round(max(samples), 3),
        "samples": [round(s, 3) for s in samples],
        "machine": {
            "platform": platform.platform(),
            "python": platform.python_version(),
            "processor": platform.processor(),
        },
    }
    if out_path is not None:
        out_path = Path(out_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(result, indent=2) + "\n")
    return result


def main() -> None:
    if not _live():
        print("skipped: set OLLAMA_LIVE=1 to run the live ingestion bench")
        return
    parser = argparse.ArgumentParser(description="Document ingestion throughput benchmark")
    parser.add_argument("--pdf", type=Path, default=None, help="sample PDF to ingest")
    parser.add_argument("--n", type=int, default=3, help="number of ingest runs")
    parser.add_argument("--out", type=Path, default=_DEFAULT_OUT, help="JSON output path")
    parser.add_argument(
        "--regex-extract", action="store_true",
        help="skip the LLM entity-extraction call (isolate parse+embed+index)",
    )
    args = parser.parse_args()

    pdf = _find_pdf(args.pdf)
    if pdf is None:
        print("skipped: no sample PDF found (pass --pdf path/to.pdf)")
        return

    result = run(pdf, n=args.n, out_path=args.out, regex_extract=args.regex_extract)
    if result is None:
        return
    print(
        f"ingest (n={result['n']}, {result['pdf']}): "
        f"median={result['median_s']}s  min={result['min_s']}s  max={result['max_s']}s"
    )
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
