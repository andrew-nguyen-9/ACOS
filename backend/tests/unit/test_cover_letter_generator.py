from unittest.mock import MagicMock
import pytest
from backend.services.cover_letter.generator import CoverLetterGenerator, LENGTH_TARGETS


def test_length_targets_defined():
    assert "short" in LENGTH_TARGETS
    assert "medium" in LENGTH_TARGETS
    assert "long" in LENGTH_TARGETS
    assert "full" in LENGTH_TARGETS
    assert LENGTH_TARGETS["short"] == 100
    assert LENGTH_TARGETS["medium"] == 250
    assert LENGTH_TARGETS["long"] == 400
    assert LENGTH_TARGETS["full"] == 600


@pytest.fixture
def mock_selector():
    sel = MagicMock()
    sel.select.return_value = [
        {
            "bullet_text": "Led Python migration saving $200K annually",
            "evidence_id": "b1",
            "experience_id": "exp1",
            "company": "Acme",
            "title": "Engineer",
            "dates": "2022–2024",
            "confidence": "verified",
        }
    ]
    return sel


@pytest.fixture
def mock_voice():
    vm = MagicMock()
    vm.get_or_create_default.return_value = {
        "profile_id": None,
        "tone_descriptors": ["professional", "confident"],
        "structure_patterns": ["hook → evidence → close"],
        "vocabulary_patterns": {
            "formal_phrases": ["I am excited"],
            "transition_words": [],
            "avoid": [],
        },
        "sample_sentences": ["I bring measurable results."],
    }
    return vm


@pytest.fixture
def mock_loader():
    loader = MagicMock()
    loader.load.return_value = {
        "version": "1.0",
        "system": "Write cover letter.",
        "user_template": (
            "JD: {job_description}\nCompany: {company}\nTitle: {job_title}\n"
            "Industry: {industry}\nLength: {length_target}\nTone: {tone_descriptors}\n"
            "Vocab: {vocabulary_patterns}\nSamples: {sample_sentences}\n"
            "Evidence: {evidence_json}\nKeywords: {keywords}"
        ),
    }
    return loader


@pytest.fixture
def mock_ollama():
    client = MagicMock()
    client.is_available.return_value = True
    # Return a 250-word text approximation
    client.generate.return_value = " ".join(["word"] * 250)
    return client


def test_generate_returns_required_keys(mock_selector, mock_voice, mock_loader, mock_ollama):
    gen = CoverLetterGenerator(mock_selector, mock_voice, mock_ollama, mock_loader)
    result = gen.generate("Python engineer role", "Acme Corp", "Engineer", "medium")
    for key in ["text", "word_count", "length_target", "requires_approval"]:
        assert key in result


def test_generate_correct_length_target(mock_selector, mock_voice, mock_loader, mock_ollama):
    gen = CoverLetterGenerator(mock_selector, mock_voice, mock_ollama, mock_loader)
    result = gen.generate("Role", "Co", "Title", "short")
    assert result["length_target"] == "short"


def test_generate_invalid_length_raises(mock_selector, mock_voice, mock_loader, mock_ollama):
    gen = CoverLetterGenerator(mock_selector, mock_voice, mock_ollama, mock_loader)
    with pytest.raises(ValueError, match="Invalid length_target"):
        gen.generate("Role", "Co", "Title", "invalid")


def test_generate_offline_returns_text(mock_selector, mock_voice, mock_loader):
    offline = MagicMock()
    offline.is_available.return_value = False
    gen = CoverLetterGenerator(mock_selector, mock_voice, offline, mock_loader)
    result = gen.generate("Role", "Co", "Title", "medium")
    assert isinstance(result["text"], str)
    assert len(result["text"]) > 0


def test_generate_weak_inference_sets_approval(mock_voice, mock_loader, mock_ollama):
    sel = MagicMock()
    sel.select.return_value = [
        {"bullet_text": "Possibly managed a team", "evidence_id": "w1",
         "experience_id": "exp1", "company": "Corp", "title": "Manager",
         "dates": "2020–2021", "confidence": "weak_inference"}
    ]
    gen = CoverLetterGenerator(sel, mock_voice, mock_ollama, mock_loader)
    result = gen.generate("Management role", "Corp", "Manager", "medium")
    assert result["requires_approval"] is True


def test_generate_llm_exception_falls_back(mock_selector, mock_voice, mock_loader):
    failing_ollama = MagicMock()
    failing_ollama.is_available.return_value = True
    failing_ollama.generate.side_effect = RuntimeError("connection refused")
    gen = CoverLetterGenerator(mock_selector, mock_voice, failing_ollama, mock_loader)
    result = gen.generate("Python role", "Co", "Dev", "medium")
    assert isinstance(result["text"], str)
    assert len(result["text"]) > 0
