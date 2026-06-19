import pytest
from backend.services.prompt_loader import PromptLoader


def test_load_returns_required_keys():
    loader = PromptLoader()
    prompt = loader.load("resume/generate")
    assert "version" in prompt
    assert "system" in prompt
    assert "user_template" in prompt


def test_load_missing_prompt_raises():
    loader = PromptLoader()
    with pytest.raises(FileNotFoundError):
        loader.load("nonexistent/prompt")


def test_load_extract_keywords():
    loader = PromptLoader()
    prompt = loader.load("resume/extract_keywords")
    assert "{job_description}" in prompt["user_template"]


def test_load_cover_letter_generate():
    loader = PromptLoader()
    prompt = loader.load("cover_letter/generate")
    assert "{job_description}" in prompt["user_template"]
    assert "{length_target}" in prompt["user_template"]
