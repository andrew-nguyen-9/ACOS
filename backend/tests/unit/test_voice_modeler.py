import json
from unittest.mock import MagicMock
import pytest
from backend.services.cover_letter.voice_modeler import VoiceModeler


@pytest.fixture
def mock_ollama():
    client = MagicMock()
    client.is_available.return_value = True
    client.generate.return_value = json.dumps({
        "tone_descriptors": ["professional", "confident", "concise"],
        "structure_patterns": ["opens with hook", "leads with value"],
        "vocabulary_patterns": {
            "formal_phrases": ["I am excited to"],
            "transition_words": ["furthermore", "additionally"],
            "avoid": ["I feel", "I think"],
        },
        "sample_sentences": ["I bring a track record of delivering measurable outcomes."],
    })
    return client


@pytest.fixture
def mock_loader():
    loader = MagicMock()
    loader.load.return_value = {
        "version": "1.0",
        "system": "Analyze writing style.",
        "user_template": "Cover Letters:\n{cover_letter_texts}\n\nReturn JSON.",
    }
    return loader


def test_learn_returns_required_keys(mock_ollama, mock_loader, test_session):
    modeler = VoiceModeler(mock_ollama, mock_loader, test_session)
    result = modeler.learn(["Dear Hiring Manager, I am writing to express my interest..."])
    for key in ["profile_id", "tone_descriptors", "structure_patterns", "vocabulary_patterns", "sample_sentences"]:
        assert key in result


def test_learn_saves_to_db(mock_ollama, mock_loader, test_session):
    modeler = VoiceModeler(mock_ollama, mock_loader, test_session)
    result = modeler.learn(["I bring strong analytical skills and a proven track record."])
    assert result["profile_id"] is not None
    assert len(result["profile_id"]) == 32


def test_learn_offline_returns_defaults(mock_loader, test_session):
    offline = MagicMock()
    offline.is_available.return_value = False
    modeler = VoiceModeler(offline, mock_loader, test_session)
    result = modeler.learn(["Some cover letter text."])
    assert isinstance(result["tone_descriptors"], list)


def test_get_or_create_default_returns_profile(mock_loader, test_session):
    offline = MagicMock()
    offline.is_available.return_value = False
    modeler = VoiceModeler(offline, mock_loader, test_session)
    result = modeler.get_or_create_default()
    assert "tone_descriptors" in result
