# Scripts

Operational tooling for ingestion, maintenance, and building. Most scripts are run from
the **repository root** so that `backend` imports resolve.

| Script | Purpose |
|--------|---------|
| `build_backend.sh` | Build the standalone backend binary (PyInstaller) used as the Tauri sidecar. |
| `generate_icons.py` | Generate Tauri desktop app icons. |
| `ingestion/ingest_static_files.py` | Ingest résumés, job descriptions, and project docs from `.static_files/` into the knowledge graph + vector store. |
| `ingestion/ingest_github.py` | Ingest GitHub repositories as project evidence. |
| `maintenance/reindex_all.py` | Rebuild all ChromaDB vector indexes from current data. |
| `seed/` | Seed-data helpers. |

## Usage

```bash
# from repo root, with the venv active
python scripts/ingestion/ingest_static_files.py
python scripts/ingestion/ingest_github.py
python scripts/maintenance/reindex_all.py

bash scripts/build_backend.sh
```

> Source data lives under `.static_files/` (git-ignored). See
> [`../docs/DATA_IMPORT.md`](../docs/DATA_IMPORT.md) for the full import workflow.
