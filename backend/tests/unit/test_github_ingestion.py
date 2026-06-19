from unittest.mock import MagicMock, patch
import pytest


def test_fetch_repos_returns_list():
    from scripts.ingestion.ingest_github import fetch_repos
    mock_response = MagicMock()
    mock_response.json.return_value = [
        {"name": "ACOS", "full_name": "andrew-nguyen-9/ACOS",
         "description": "Career OS", "language": "Python",
         "html_url": "https://github.com/andrew-nguyen-9/ACOS",
         "default_branch": "main"},
    ]
    mock_response.raise_for_status = MagicMock()
    with patch("httpx.get", return_value=mock_response):
        repos = fetch_repos("andrew-nguyen-9")
    assert len(repos) == 1
    assert repos[0]["name"] == "ACOS"


def test_fetch_readme_returns_text():
    from scripts.ingestion.ingest_github import fetch_readme
    mock_response = MagicMock()
    mock_response.text = "# ACOS\nCareer OS for Andrew."
    mock_response.raise_for_status = MagicMock()
    with patch("httpx.get", return_value=mock_response):
        text = fetch_readme("andrew-nguyen-9", "ACOS", "main")
    assert "ACOS" in text


def test_fetch_readme_returns_empty_on_404():
    from scripts.ingestion.ingest_github import fetch_readme
    import httpx
    with patch("httpx.get", side_effect=httpx.HTTPStatusError("404", request=MagicMock(), response=MagicMock())):
        text = fetch_readme("andrew-nguyen-9", "no-readme-repo", "main")
    assert text == ""
