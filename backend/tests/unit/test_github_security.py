from __future__ import annotations

from unittest.mock import MagicMock, patch
import pytest


def test_fetch_readme_truncates_oversized_content():
    """README content must be capped at 50KB to prevent OOM on adversarial repos."""
    from scripts.ingestion.ingest_github import fetch_readme
    huge_readme = "A" * (200_000)
    mock_response = MagicMock()
    mock_response.text = huge_readme
    mock_response.raise_for_status = MagicMock()
    with patch("httpx.get", return_value=mock_response):
        text = fetch_readme("user", "repo", "main")
    assert len(text) <= 51_200  # 50 KB cap


def test_ingest_text_is_size_capped():
    """The text assembled for indexing must be ≤50KB before extraction."""
    from scripts.ingestion.ingest_github import _build_repo_text
    oversized_readme = "X" * 200_000
    repo = {
        "name": "myrepo",
        "description": "A great repo",
        "language": "Python",
        "html_url": "https://github.com/user/myrepo",
    }
    text = _build_repo_text(repo, oversized_readme)
    assert len(text) <= 51_200
