"""Phase 11.9 RCL-003: tone parameter for cover-letter generation."""
from unittest.mock import MagicMock

from backend.services.cover_letter.generator import (
    CoverLetterGenerator,
    tone_descriptor,
)


def test_tone_descriptor_bands():
    assert "traditional" in tone_descriptor(0.0).lower()
    assert "balanced" in tone_descriptor(0.5).lower()
    assert "bold" in tone_descriptor(1.0).lower()


def test_tone_descriptor_clamps_out_of_range():
    assert tone_descriptor(-5.0) == tone_descriptor(0.0)
    assert tone_descriptor(5.0) == tone_descriptor(1.0)


def _mocks():
    sel = MagicMock()
    sel.select.return_value = [
        {"bullet_text": "Led Python migration", "evidence_id": "b1",
         "experience_id": "e1", "company": "Acme", "title": "Eng",
         "dates": "2022", "confidence": "verified"}
    ]
    voice = MagicMock()
    voice.get_or_create_default.return_value = {
        "profile_id": None, "tone_descriptors": ["professional"],
        "vocabulary_patterns": {}, "sample_sentences": [],
    }
    loader = MagicMock()
    loader.load.return_value = {
        "version": "1.0", "system": "sys",
        "user_template": (
            "JD:{job_description} Co:{company} Title:{job_title} Ind:{industry} "
            "Len:{length_target} Tone:{tone_descriptors} Vocab:{vocabulary_patterns} "
            "Samples:{sample_sentences} Ev:{evidence_json} Kw:{keywords} "
            "Sel:{selected_bullets_json} Exc:{excluded_bullets_json}"
        ),
    }
    ollama = MagicMock()
    ollama.is_available.return_value = True
    ollama.generate.return_value = " ".join(["word"] * 250)
    return sel, voice, loader, ollama


def test_bold_tone_reaches_the_prompt():
    sel, voice, loader, ollama = _mocks()
    gen = CoverLetterGenerator(sel, voice, ollama, loader)
    gen.generate("Role", "Co", "Title", "medium", tone=1.0)
    prompt = ollama.generate.call_args.kwargs["prompt"]
    assert "bold" in prompt.lower()


def test_tone_omitted_keeps_default_voice():
    sel, voice, loader, ollama = _mocks()
    gen = CoverLetterGenerator(sel, voice, ollama, loader)
    gen.generate("Role", "Co", "Title", "medium")
    prompt = ollama.generate.call_args.kwargs["prompt"]
    assert "professional" in prompt.lower()
    assert "bold" not in prompt.lower()
