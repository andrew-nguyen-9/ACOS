#!/usr/bin/env bash
# scripts/build_backend.sh
# Builds the FastAPI backend into a PyInstaller one-file binary and places it
# as a Tauri external-bin sidecar in frontend/src-tauri/binaries/.
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
BINARY_DIR="$REPO_ROOT/frontend/src-tauri/binaries"

cd "$REPO_ROOT"
source .venv/bin/activate

echo "→ Installing PyInstaller…"
pip install "pyinstaller>=6.0" --quiet

echo "→ Building backend binary…"
pyinstaller acos-backend.spec --noconfirm --distpath "$REPO_ROOT/dist/backend"

# Detect the Rust/Tauri target triple.
# Tauri names sidecars as <name>-<triple>, so the binary must match exactly.
if command -v rustc &>/dev/null; then
    TRIPLE=$(rustc --print target-triple)
else
    TRIPLE=$(python3 -c "
import platform
m = platform.machine().lower()
if m == 'arm64':
    print('aarch64-apple-darwin')
elif m == 'x86_64':
    print('x86_64-apple-darwin')
else:
    print('unknown-apple-darwin')
")
fi

echo "→ Target triple: $TRIPLE"

DEST="$BINARY_DIR/acos-backend-$TRIPLE"
cp "$REPO_ROOT/dist/backend/acos-backend" "$DEST"
chmod +x "$DEST"
echo "✓ Binary placed at $DEST"
