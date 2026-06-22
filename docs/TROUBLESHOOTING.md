# ACOS Troubleshooting Guide

This guide covers the most common issues and their fixes. For each symptom, start
with the listed checks before moving on.

---

## Backend Not Starting

**Symptom:** App shows a spinner indefinitely; the first-run wizard never loads.

**Checks:**

1. Verify the backend binary exists:
   ```bash
   ls frontend/src-tauri/binaries/
   ```

2. Test the binary directly (substitute your target triple from `rustc --print target-triple`):
   ```bash
   ./frontend/src-tauri/binaries/acos-backend-aarch64-apple-darwin &
   sleep 2
   curl http://127.0.0.1:8000/api/v1/health
   ```

3. Check whether port 8000 is already occupied:
   ```bash
   lsof -i :8000
   ```
   If another process is listed, stop it or change the backend port.

4. In development mode (not packaged), start the backend manually:
   ```bash
   source .venv/bin/activate
   uvicorn backend.main:app --port 8000
   ```

5. Confirm the health endpoint responds:
   ```bash
   curl http://localhost:8000/api/v1/health
   # Expected: {"status": "ok", ...}
   ```

---

## Ollama Not Detected

**Symptom:** First-run wizard shows "Ollama not found" on the Ollama Check step.

**Checks:**

1. Confirm Ollama is installed:
   ```bash
   which ollama
   ollama --version
   ```

2. Start Ollama if it is not running:
   ```bash
   ollama serve
   # or open Ollama.app from /Applications
   ```

3. Pull the required models:
   ```bash
   ollama pull qwen3:8b
   ollama pull nomic-embed-text
   ```

4. Verify Ollama responds on its default port:
   ```bash
   curl http://localhost:11434/api/tags
   ```

5. In ACOS, click **Re-check** in the wizard.

6. Confirm via the ACOS health endpoint:
   ```bash
   curl http://localhost:8000/api/v1/health/ollama
   ```
   The response lists `available_models` and `missing_models`. If models appear in
   `missing_models` despite being pulled, see the next section.

---

## Model Missing After Pull

**Symptom:** `GET /api/v1/health/ollama` shows `qwen3:8b` in `missing_models` even
after `ollama pull`.

**Explanation:** The health check matches on the base model name (the part before
the first `:`). A pull that downloaded `qwen3:8b-instruct` would not match `qwen3:8b`.

**Fix:**

```bash
ollama list | grep qwen3
```

Confirm the exact name is `qwen3:8b`. If you see a variant (e.g., `qwen3:8b-instruct`),
either pull the exact tag or update the `default_model` setting to match the
installed name:

```bash
curl -X PUT http://localhost:8000/api/v1/settings/default_model \
  -H "Content-Type: application/json" \
  -d '{"value": "qwen3:8b-instruct"}'
```

If the model name is correct but the check still fails, restart Ollama:

```bash
pkill ollama && ollama serve
```

---

## Ingestion Fails (422 or 500)

**Symptom:** `POST /api/v1/ingest` returns a 422 or 500 error.

**Checks:**

- **Wrong file type:** Only PDF, DOCX, TXT, and Markdown (`.md`) are supported.
  All other MIME types are rejected with 422.

- **File too large:** The limit is 10 MB. Files over this size are rejected.

- **Path traversal:** Filenames containing `..` or `/` are blocked by the sanitizer.
  Rename the file and retry.

- **Check the response from the POST:** Ingestion is synchronous; the `POST /api/v1/ingest` response includes `ingestion_status`. If it is `"failed"`, the embedding step raised an error.

- **Embedding failure:** Verify Ollama is running and `nomic-embed-text` is available:
  ```bash
  curl http://localhost:8000/api/v1/health/ollama
  ollama pull nomic-embed-text   # if missing
  ```

---

## Resume Generation Returns Empty or Generic Results

**Symptom:** `POST /api/v1/resume/generate` returns 200 but sections are empty or
bullets are not grounded in your experience.

**Root cause:** The resume generator retrieves evidence via RAG. If no documents
have been ingested, there is nothing to draw from and the model falls back to
generic output.

**Fix:**

1. Ingest your existing resume:
   ```bash
   curl -X POST http://localhost:8000/api/v1/ingest \
     -F "file=@/path/to/your-resume.pdf"
   ```

2. Ingest your experience bank:
   ```bash
   curl -X POST http://localhost:8000/api/v1/ingest \
     -F "file=@.static_files/profile/experience-bank.md"
   ```

3. Run the full seed script to import everything at once:
   ```bash
   source .venv/bin/activate
   python scripts/ingestion/ingest_static_files.py
   ```

4. Re-generate the resume.

---

## ChromaDB Errors at Startup

**Symptom:** Backend logs contain `chromadb.errors.InvalidCollectionException`,
`Segment not found`, or similar ChromaDB errors.

**Fix:** Re-initialize all ChromaDB collections:

```bash
source .venv/bin/activate
python scripts/maintenance/reindex_all.py
```

This is safe and idempotent. If the error persists, the chroma directory may be
corrupted. Delete it and re-run:

```bash
rm -rf ~/.acos/chroma
python scripts/maintenance/reindex_all.py
```

Note: deleting the chroma directory removes all embeddings. You will need to
re-run the ingestion seed script afterwards.

---

## ATS Score Always 0 or 100

**Symptom:** ATS scores look wrong (always zero, always perfect) regardless of the
job description.

**Root cause:** The ATS scorer extracts keywords from the job description. Very short
or overly generic JDs yield extreme scores.

**Fix:** Provide the full job description text, not just the job title or a summary.
The keyword extractor needs at least 100 words to generate a meaningful keyword set.
Copy the entire posting (responsibilities, requirements, and preferred qualifications)
into the request body.

---

## Copilot Gives Irrelevant Responses

**Symptom:** The copilot answers generic questions that ignore your actual background.

**Root cause:** Same as empty resume generation — no documents have been ingested
into the knowledge graph.

**Fix:** Follow the ingestion steps in the Resume Generation section above. The
copilot uses the same ChromaDB collections as the resume generator.

---

## App Crashes on Launch (macOS)

**Symptom:** ACOS.app bounces in the Dock and closes immediately.

**Checks:**

1. Open Console.app, filter by process name `acos`, and check for crash logs.

2. A common cause is a missing or unsigned backend binary. Rebuild it:
   ```bash
   bash scripts/build_backend.sh
   ```
   Then rebuild the Tauri app.

3. If crash logs show `killed: 9` (SIGKILL), Gatekeeper may be quarantining the
   binary. Remove the quarantine attribute:
   ```bash
   xattr -dr com.apple.quarantine /Applications/ACOS.app
   ```

4. If the app quits with a Tauri error about `externalBin`, confirm the binary name
   matches the target triple:
   ```bash
   rustc --print target-triple
   ls frontend/src-tauri/binaries/
   ```
   The binary must be named `acos-backend-<target-triple>` (no file extension).

---

## Settings Not Persisting

**Symptom:** Changes made in ACOS Settings revert after restarting the app.

**Fix:** Settings are stored in the `system_config` table of `~/.acos/acos.db`.
Check that the database file is writable:

```bash
ls -la ~/.acos/acos.db
```

If permissions are wrong:
```bash
chmod 644 ~/.acos/acos.db
```

To verify a setting was saved:
```bash
curl http://localhost:8000/api/v1/settings
```

---

## Visual Effects / WebGL Material (Phase 11.7)

**Symptom:** background looks flat (no animated material), or the GPU runs hot / the
fan spins, or you want to turn the effects off.

**Disable the effects:** Settings → **Visual Effects** → **Off** (or **Reduced**).
The choice persists in `localStorage` (`acos:visual-effects`) and applies live — no
restart. `Off` falls back to the cheap static aurora; the app is fully functional on
every tier (the WebGL material is decoration, never a requirement).

**Why the material isn't showing (it's expected, not a bug) when:**
- The display/GPU has **no WebGL** — `capability.ts` resolves the tier to `Off`. The
  Settings panel shows a note when WebGL is unavailable.
- **OS reduced-motion** is on (macOS: System Settings → Accessibility → Display →
  Reduce motion) — the tier resolves to `Off` by design.
- The window is **hidden or blurred** — the App-Nap clock parks the render loop
  (`clock.ts`, DMI-003) so the canvas costs ~0 in the background; it resumes on focus.
- The GPU **lost the WebGL context** (`webglcontextlost`) — the canvas unmounts to the
  static aurora automatically. Switch the tier Off→Full in Settings to remount.

**CSP note:** `three` + `@react-three/fiber` need no `eval`, `wasm`, Web Worker, or
`blob:` URL for this material, so the Tauri CSP (`src-tauri/tauri.conf.json`,
`script-src 'self'`) is **unchanged** by 11.7. If a *future* shader uses a Web Worker
or `Blob:` URL, add `worker-src 'self' blob:` to the CSP — and always test the
**production** Tauri build (`npm run tauri build`), not just `vite dev`, because CSP is
enforced in the packaged app, not the dev server.

## Getting More Debug Information

Enable verbose backend logging by starting the backend with the `--log-level debug` flag:

```bash
source .venv/bin/activate
uvicorn backend.main:app --port 8000 --log-level debug
```

Or set the environment variable before launching the packaged app:

```bash
ACOS_LOG_LEVEL=debug open /Applications/ACOS.app
```

---

## See Also

- [User Guide](USER_GUIDE.md) — end-to-end usage walkthrough
- [Model Setup Guide](MODEL_SETUP.md) — Ollama installation and model management
- [Data Import Guide](DATA_IMPORT.md) — importing professional history
- [Architecture Overview](ARCHITECTURE_OVERVIEW.md) — system internals
