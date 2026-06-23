"""Fast token counting for num_ctx budgeting.

# ponytail: a ~4 chars/token heuristic is fine for sizing the context window —
# we only need to pick a 2048/4096 bucket, not an exact qwen3 token count. If
# tiktoken is already installed we use cl100k (closer), but we never add it as a
# dependency just for budgeting.
"""
from __future__ import annotations

try:
    import tiktoken  # pyright: ignore[reportMissingImports]

    _ENC = tiktoken.get_encoding("cl100k_base")
except Exception:  # pragma: no cover - tiktoken is optional
    _ENC = None


def count_tokens(text: str) -> int:
    if not text:
        return 0
    if _ENC is not None:  # pragma: no cover - only when tiktoken present
        return len(_ENC.encode(text))
    # 4 chars/token approximation, rounded up so we never under-budget the window.
    return -(-len(text) // 4)
