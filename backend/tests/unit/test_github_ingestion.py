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


def test_ingest_indexes_with_github_doc_type():
    """Guard against indexer-signature drift (12.6): the github path must call
    index_document(doc_id, text, metadata, doc_type='acos_github')."""
    import scripts.ingestion.ingest_github as gh

    mock_indexer = MagicMock()
    repo = {"name": "ACOS", "default_branch": "main", "html_url": "u", "language": "Python"}
    with patch.object(gh, "OllamaClient"), patch.object(gh, "Embedder"), \
            patch.object(gh, "ChromaManager"), patch.object(gh, "EntityExtractor"), \
            patch.object(gh, "KnowledgeGraphService"), patch.object(gh, "SessionLocal"), \
            patch.object(gh, "get_settings"), \
            patch.object(gh, "RAGIndexer", return_value=mock_indexer), \
            patch.object(gh, "fetch_repos", return_value=[repo]), \
            patch.object(gh, "fetch_readme", return_value="# readme"):
        gh.ingest("andrew-nguyen-9")

    mock_indexer.index_document.assert_called_once()
    kwargs = mock_indexer.index_document.call_args.kwargs
    assert kwargs["doc_type"] == "acos_github"
    # doc_id is first positional, metadata is a dict (not a collection-name string)
    args = mock_indexer.index_document.call_args.args
    assert args[0] == "github_andrew-nguyen-9_ACOS"
    assert isinstance(args[2], dict)
