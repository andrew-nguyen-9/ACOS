from __future__ import annotations

from backend.services.intelligence.skill_normalizer import SkillNormalizer


def test_expands_known_alias_in_text() -> None:
    n = SkillNormalizer()
    assert "machine learning" in n.normalize("Built an ML model").lower()


def test_alias_replacement_is_case_insensitive() -> None:
    n = SkillNormalizer()
    out = n.normalize("Applied NLP and ml techniques").lower()
    assert "natural language processing" in out
    assert "machine learning" in out


def test_does_not_touch_substrings_of_other_words() -> None:
    # "ml" inside "HTML" must not be expanded
    n = SkillNormalizer()
    assert "HTML" in n.normalize("Wrote HTML pages")


def test_normalize_list_canonicalizes_and_dedups() -> None:
    n = SkillNormalizer()
    out = n.normalize_list(["ML", "machine learning", "A/B"])
    assert out.count("machine learning") == 1
    assert "A/B testing" in out


def test_unknown_skill_passthrough() -> None:
    n = SkillNormalizer()
    assert n.normalize_list(["Rust"]) == ["Rust"]
