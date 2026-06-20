# Data Import Guide

ACOS becomes more powerful as you populate it with your professional history. This
guide covers every import method: the bulk seed script, the file upload API, GitHub
ingestion, and manual application entry.

---

## Before You Start

The backend must be running and Ollama must be available before importing. Confirm:

```bash
curl http://localhost:8000/api/v1/health
curl http://localhost:8000/api/v1/health/ollama
```

Both should return `"status": "ok"` (or `"ollama_available": true`). If Ollama is
not available, embeddings will fail. See [Model Setup Guide](MODEL_SETUP.md).

---

## Quick Start: Static Files Seed Script

If you have existing documents in `.static_files/`, run the seed script to import
everything at once:

```bash
source .venv/bin/activate
python scripts/ingestion/ingest_static_files.py
```

This script imports the following in order:

| Source path | What it imports |
|-------------|----------------|
| `.static_files/profile/resume.txt` | Structured resume |
| `.static_files/profile/experience-bank.md` | Detailed experience bank |
| `.static_files/profile/cv.txt` | Full CV |
| `.static_files/profile/cover-letters/*.{txt,md,docx}` | Cover letters (voice learning) |
| `.static_files/job-descriptions/*/jd.txt` | Historical job descriptions |
| `.static_files/job-descriptions/*/application-answers.md` | Historical Q&A answers |

The script is idempotent — running it a second time skips documents that have
already been ingested (matched by filename hash).

---

## API Import: Single Document Upload

Use `POST /api/v1/ingest` to upload one document at a time.

**Supported formats:** PDF, DOCX, TXT, Markdown (`.md`)
**File size limit:** 10 MB

```bash
curl -X POST http://localhost:8000/api/v1/ingest \
  -F "file=@/path/to/resume.pdf"
```

### Response

```json
{
  "id": "b3d12f8a-...",
  "filename": "resume.pdf",
  "ingestion_status": "processing"
}
```

Ingestion is asynchronous. The document is parsed and embedded in the background.
Poll for completion using the returned `id`:

```bash
curl http://localhost:8000/api/v1/ingest/b3d12f8a-...
```

### Ingestion Status Values

| Status | Meaning |
|--------|---------|
| `queued` | Waiting for a worker slot |
| `processing` | Currently being parsed and embedded |
| `complete` | Fully embedded and searchable |
| `failed` | An error occurred; check Ollama availability |

When `ingestion_status` is `"complete"`, the document's entities and embeddings
are available to the resume generator, cover letter generator, and copilot.

### Batch Upload (Shell Loop)

To import a directory of files:

```bash
for f in /path/to/documents/*.pdf; do
  curl -s -X POST http://localhost:8000/api/v1/ingest \
    -F "file=@$f" | python3 -m json.tool
done
```

---

## API Import: GitHub Repository README

ACOS can ingest a GitHub repository's README as a context document (useful for
importing open-source projects you have contributed to):

```bash
curl -X POST http://localhost:8000/api/v1/ingest/github \
  -H "Content-Type: application/json" \
  -d '{"owner": "andrew-nguyen-9", "repo": "my-project"}'
```

The README is fetched over HTTPS. The size limit is 50 KB — larger READMEs are
truncated to prevent memory issues during embedding.

---

## Importing Job Applications

### Via the Seed Script (Automatic)

If your historical job description directories contain a `meta.json` file, the seed
script imports them as `Application` records automatically. Expected format:

```json
{
  "company": "Acme Corp",
  "position": "Senior Product Manager",
  "industry": "Technology",
  "status": "rejected",
  "date_applied": "2025-09-15"
}
```

Check whether your directories have these files:

```bash
find .static_files/job-descriptions -name meta.json | head -5
```

### Via the API (Manual)

```bash
curl -X POST http://localhost:8000/api/v1/applications \
  -H "Content-Type: application/json" \
  -d '{
    "company": "Acme Corp",
    "position": "Senior PM",
    "industry": "Technology",
    "status": "applied",
    "date_applied": "2026-06-01"
  }'
```

Valid `status` values:

```
draft → applied → phone_screen → interview → final_round → offer
                                                          → rejected
                                                          → withdrawn
```

### Listing All Applications

```bash
curl http://localhost:8000/api/v1/applications | python3 -m json.tool
```

---

## Importing the Question Bank

Historical application answers (behavioral questions, written responses) are
indexed into the question bank for reuse in future applications.

### Via the API

```bash
curl -X POST http://localhost:8000/api/v1/questions/import-answers \
  -F "file=@.static_files/job-descriptions/acme-corp/application-answers.md"
```

The file should be a Markdown document with question-answer pairs. The importer
extracts Q&A blocks and embeds them into the `questions` and `outcomes` ChromaDB
collections.

### Via the Seed Script

The seed script handles all `application-answers.md` files in
`.static_files/job-descriptions/` automatically. No separate step is needed if
you use the seed script.

---

## Document Formats: Parser Details

| Format | Parser | Notes |
|--------|--------|-------|
| PDF | pypdf | Text extraction only; scanned PDFs (image-only) yield empty output |
| DOCX | python-docx | Tables and formatting are preserved as plain text |
| TXT | built-in | UTF-8 expected; other encodings are detected and converted |
| Markdown | mistune | Front matter is stripped; headers become section boundaries |

**Tip:** For best entity extraction, prefer DOCX or Markdown over PDF. PDFs from
word processors work well; PDFs created from scans or images do not.

---

## Viewing All Ingested Documents

```bash
curl http://localhost:8000/api/v1/ingest | python3 -m json.tool
```

Key fields in the response:

| Field | Description |
|-------|-------------|
| `id` | Document UUID |
| `filename` | Original filename |
| `ingestion_status` | `queued`, `processing`, `complete`, or `failed` |
| `entity_count` | Number of structured entities extracted |
| `embedding_status` | Whether ChromaDB embedding is complete |
| `created_at` | ISO 8601 timestamp of upload |

---

## Re-Indexing

Re-indexing rebuilds all ChromaDB embeddings from the current documents in
SQLite. Run this after:

- Changing the embedding model (`nomic-embed-text` → another model)
- Recovering from a corrupted `~/.acos/chroma/` directory
- A ChromaDB version upgrade

```bash
source .venv/bin/activate
python scripts/maintenance/reindex_all.py
```

This is safe and idempotent. It deletes and recreates all ten ChromaDB
collections from the `documents` table in SQLite. No document data is lost.

You can also trigger re-indexing via the API:

```bash
curl -X POST http://localhost:8000/api/v1/learning/reindex
```

---

## Storage Locations

| Path | Contents |
|------|---------|
| `~/.acos/acos.db` | SQLite database — all structured data |
| `~/.acos/chroma/` | ChromaDB — all vector embeddings |
| `.static_files/profile/` | Source resume, experience bank, cover letters |
| `.static_files/job-descriptions/` | Historical JD text and Q&A answers |

---

## Troubleshooting Import Issues

**Ingestion stuck in `processing` for more than a few minutes**

Ollama may be unresponsive. Check:

```bash
curl http://localhost:8000/api/v1/health/ollama
```

Restart Ollama if needed: `pkill ollama && ollama serve`

**Ingestion status is `failed`**

Check that `nomic-embed-text` is available:

```bash
ollama list | grep nomic
ollama pull nomic-embed-text   # if missing
```

**PDF yields no entity extractions (`entity_count: 0`)**

The PDF may be a scanned image. Convert it to DOCX or TXT using a tool such as
`pdftotext` (from Poppler) and re-ingest the text file:

```bash
pdftotext /path/to/resume.pdf /path/to/resume.txt
curl -X POST http://localhost:8000/api/v1/ingest \
  -F "file=@/path/to/resume.txt"
```

---

## See Also

- [User Guide](USER_GUIDE.md) — end-to-end usage walkthrough
- [Model Setup Guide](MODEL_SETUP.md) — Ollama installation and model management
- [Troubleshooting](TROUBLESHOOTING.md) — common issues and fixes
- [Architecture Overview](ARCHITECTURE_OVERVIEW.md) — how ingestion fits into the system
