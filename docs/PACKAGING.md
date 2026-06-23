# Packaging — macOS DMG (Phase 13.8)

ACOS ships as a Tauri v2 desktop app that bundles the React frontend **and** the
Python backend (as a PyInstaller one-file *sidecar*). Ollama is **not** bundled — it
is a documented external prerequisite (see [`MODEL_SETUP.md`](./MODEL_SETUP.md)).

> Trap-1 (from Phase 12.5) is binding: `lib.rs` spawns the **Python sidecar**, not
> Ollama. The DMG carries the app + sidecar; the user installs Ollama separately and
> the first-run wizard checks for it.

---

## What's in the bundle

| Component | How it's packaged |
|-----------|-------------------|
| Frontend (React/Vite) | `frontendDist: ../dist`, built by `beforeBuildCommand` |
| Backend (FastAPI) | PyInstaller one-file binary, declared as `bundle.externalBin: binaries/acos-backend` |
| Ollama + models | **External** — not bundled (`MODEL_SETUP.md`) |

The sidecar path resolves itself: `lib.rs` spawns it via
`app.shell().sidecar("acos-backend")`, and Tauri locates the target-triple-suffixed
binary inside the app bundle (`…/Contents/MacOS/acos-backend`). The classic dev-vs-
bundle path break does not apply — there is no hardcoded path.

---

## Build

```bash
# one command: builds the sidecar, then the app + DMG
scripts/build_dmg.sh
```

Output: `frontend/src-tauri/target/release/bundle/dmg/ACOS_<version>_<arch>.dmg`.

`build_dmg.sh` runs `scripts/build_backend.sh` first. That script names the sidecar
`acos-backend-<target-triple>` (e.g. `acos-backend-aarch64-apple-darwin`) — the exact
name Tauri's `externalBin` resolution requires.

---

## Signing & notarization

Signing/notarization is **env-var driven** — Tauri reads these at build time, so no
secret is committed (CLAUDE.md). Set them in the shell that runs `build_dmg.sh`:

| Variable | Purpose |
|----------|---------|
| `APPLE_SIGNING_IDENTITY` | `"Developer ID Application: Name (TEAMID)"` — find via `security find-identity -v -p codesigning` |
| `APPLE_ID`, `APPLE_PASSWORD`, `APPLE_TEAM_ID` | Apple ID + app-specific password + team ID, for notarization |

Hardened-runtime entitlements (`src-tauri/Entitlements.plist`) are required for the
PyInstaller sidecar to run under notarization — they allow the JIT/executable memory,
`DYLD_*` env vars, and bundled-extension loading the bootloader needs. Tauri 1.5+
signs the sidecar too, so notarization covers it.

**No certificate?** The build still produces a working DMG, but it is **unsigned**:
macOS Gatekeeper warns on first launch. The user must right-click → **Open** →
**Open** once (or `xattr -dr com.apple.quarantine /Applications/ACOS.app`). This is
the honest fallback — ACOS does not pretend an unsigned build "just works."

---

## Release verification (run on the release machine)

`tauri build`, signing, install, launch, and cold-start measurement require a real
macOS release machine with the toolchain (and, for signing, an Apple cert). Run and
record:

1. `scripts/build_dmg.sh` → DMG produced. ☐
2. Open the DMG, drag **ACOS** to Applications, launch. ☐
3. First launch shows the **first-run wizard** (the onboarding-done flag is unset on a
   fresh machine — 13.5/13.7). ☐
4. Wizard: Ollama check → (pull a model if missing, 13.7) → upload a document (13.5) →
   Finish. ☐
5. Core path: generate a résumé / ask the copilot — the sidecar responds. ☐
6. **Cold-start (ms):** time from app launch to backend `/health` ready. Record the
   number here — it is the gate for reopening backlog item 12.9.3 (Nuitka) if it
   exceeds 400 ms:

   ```
   Cold-start: ____ ms   (machine: ________, date: ________)
   ```

Until these boxes are checked on real hardware, packaging is **configured and
buildable but not release-verified** — stated honestly, like the 11.8 native-haptics
note.

---

## Windows / Linux

Deferred (roadmap backlog 13.8.1 / 13.8.2). Each needs its own bundle target + signing
config; build only when explicitly requested.

---

## Auto-update (Phase 13.9 — ADR-011)

The packaged app checks **one** signed update channel (the local-only default is
overridden for updates only — see [ADR-011](./adr/ADR-011-background-auto-update-network-boundary.md)).

1. **Generate the updater keypair once** (private key stays out-of-repo, never committed):
   ```bash
   cd frontend && npm run tauri signer generate -- -w ~/.tauri/acos-updater.key
   ```
2. Put the printed **public** key in `tauri.conf.json > plugins.updater.pubkey`
   (replace `REPLACE_AT_RELEASE_WITH_TAURI_SIGNER_PUBKEY`).
3. Sign builds by exporting the private key before `build_dmg.sh`:
   ```bash
   export TAURI_SIGNING_PRIVATE_KEY="$(cat ~/.tauri/acos-updater.key)"
   export TAURI_SIGNING_PRIVATE_KEY_PASSWORD="…"
   ```
4. Publish the generated `latest.json` manifest + signed artifacts to the update
   endpoint (`https://releases.acos.app/...`, the single CSP-allowed origin).

The updater verifies each artifact's signature against the bundled pubkey **before**
applying; a tampered or unsigned artifact is rejected and the current version stays
intact. No telemetry is sent — only the version-check GET and the artifact fetch.
