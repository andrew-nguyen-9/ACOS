#!/usr/bin/env bash
# Phase 12.5 — Ollama memory/TTFT calibration for ACOS on a 16GB M1.
#
# ACOS does NOT spawn the Ollama daemon (the Tauri sidecar launches the Python
# backend, not Ollama). So the KV-cache + flash-attention env vars must be set on
# the daemon you run. This script:
#   1. exports them for the CURRENT shell and prints how to make them permanent;
#   2. pulls the pinned model tags ACOS expects.
#
# Run BEFORE `ollama serve` (env is read at daemon start):
#   source scripts/setup_ollama.sh   # source, so the exports reach `ollama serve`
set -euo pipefail

# --- Calibration env (must be set in the daemon's environment) ---------------
# Flash attention reduces memory growth as context size increases; q8_0 KV-cache
# quantization roughly halves KV memory with negligible quality loss. q8_0
# REQUIRES flash attention.
export OLLAMA_FLASH_ATTENTION=1
export OLLAMA_KV_CACHE_TYPE=q8_0

echo "set OLLAMA_FLASH_ATTENTION=$OLLAMA_FLASH_ATTENTION"
echo "set OLLAMA_KV_CACHE_TYPE=$OLLAMA_KV_CACHE_TYPE"
echo
echo "To persist for the macOS Ollama.app daemon (launchd reads these):"
echo "  launchctl setenv OLLAMA_FLASH_ATTENTION 1"
echo "  launchctl setenv OLLAMA_KV_CACHE_TYPE q8_0"
echo "  # then quit and reopen Ollama.app"
echo

# --- Pinned model tags -------------------------------------------------------
# Pin explicit quant so every machine runs the same weights. qwen3:8b ships
# Q4_K_M by default; nomic-embed-text is F16. Re-pulling the same tag is a no-op
# once present.
GEN_TAG="${ACOS_GEN_TAG:-qwen3:8b}"          # Q4_K_M default quant
EMBED_TAG="${ACOS_EMBED_TAG:-nomic-embed-text}"

echo "pulling $GEN_TAG ..."
ollama pull "$GEN_TAG"
echo "pulling $EMBED_TAG ..."
ollama pull "$EMBED_TAG"

echo
echo "done. verify quant with: ollama show $GEN_TAG | grep -i quant"
