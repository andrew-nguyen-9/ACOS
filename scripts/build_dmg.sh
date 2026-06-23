#!/usr/bin/env bash
# scripts/build_dmg.sh
# Phase 13.8 — produce a distributable macOS DMG: build the PyInstaller sidecar,
# then `tauri build` the app + DMG, signing/notarizing when credentials are present.
#
# Signing + notarization are driven entirely by environment variables (Tauri reads
# them at build time — see docs/PACKAGING.md). With NONE set, this still produces a
# working but UNSIGNED DMG that Gatekeeper will warn about on first launch.
#
#   APPLE_SIGNING_IDENTITY  "Developer ID Application: Name (TEAMID)"  (sign)
#   APPLE_ID / APPLE_PASSWORD / APPLE_TEAM_ID                          (notarize)
#
# Ollama is NOT bundled — it is a documented external prerequisite (MODEL_SETUP.md).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "→ [1/2] Building Python sidecar (PyInstaller)…"
"$SCRIPT_DIR/build_backend.sh"

echo "→ [2/2] Building Tauri app + DMG…"
cd "$REPO_ROOT/frontend"
if [[ -n "${APPLE_SIGNING_IDENTITY:-}" ]]; then
  echo "  signing identity: $APPLE_SIGNING_IDENTITY"
else
  echo "  ⚠ no APPLE_SIGNING_IDENTITY — building UNSIGNED (Gatekeeper will warn)."
fi
npm run tauri build -- --bundles dmg

echo "✓ DMG built under frontend/src-tauri/target/release/bundle/dmg/"
echo "  Verify on the release machine: see docs/PACKAGING.md → 'Release verification'."
