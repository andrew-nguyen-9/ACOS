"""Phase 14.3 — optional at-rest field encryption (ADR-013).

The guarantee, tested honestly: OFF is byte-identical passthrough; ON round-trips
and stores ciphertext; flipping ON over pre-existing plaintext doesn't brick reads.
"""
from __future__ import annotations

import pytest

from backend.config import get_settings
from backend.security.encryption import EncryptedText, encryption_enabled


@pytest.fixture
def fernet_key():
    fernet = pytest.importorskip("cryptography.fernet")
    return fernet.Fernet.generate_key().decode()


def _enable(monkeypatch, key: str) -> None:
    monkeypatch.setenv("ACOS_ENABLE_ENCRYPTED_STORAGE", "1")
    monkeypatch.setenv("ACOS_ENCRYPTION_KEY", key)
    get_settings.cache_clear()


def test_off_path_is_byte_identical_passthrough(monkeypatch):
    monkeypatch.delenv("ACOS_ENABLE_ENCRYPTED_STORAGE", raising=False)
    get_settings.cache_clear()
    try:
        assert encryption_enabled() is False
        t = EncryptedText()
        # bind then result returns the exact same string — no transform applied
        bound = t.process_bind_param("recruiter said yes", None)
        assert bound == "recruiter said yes"
        assert t.process_result_value(bound, None) == "recruiter said yes"
        assert t.process_bind_param(None, None) is None
    finally:
        get_settings.cache_clear()


def test_on_path_round_trips_and_stores_ciphertext(monkeypatch, fernet_key):
    _enable(monkeypatch, fernet_key)
    try:
        t = EncryptedText()
        plaintext = "private note: salary expectation 180k"
        stored = t.process_bind_param(plaintext, None)
        assert stored != plaintext  # encrypted at rest
        assert "salary" not in stored  # ciphertext leaks no plaintext
        assert t.process_result_value(stored, None) == plaintext
    finally:
        get_settings.cache_clear()


def test_on_path_reads_legacy_plaintext_unchanged(monkeypatch, fernet_key):
    """A value written before the flag was flipped isn't a token → returned as-is."""
    _enable(monkeypatch, fernet_key)
    try:
        assert EncryptedText().process_result_value("legacy plain note", None) == (
            "legacy plain note"
        )
    finally:
        get_settings.cache_clear()


def test_enabled_without_key_raises(monkeypatch, fernet_key):
    monkeypatch.setenv("ACOS_ENABLE_ENCRYPTED_STORAGE", "1")
    monkeypatch.delenv("ACOS_ENCRYPTION_KEY", raising=False)
    get_settings.cache_clear()
    try:
        with pytest.raises(RuntimeError, match="ACOS_ENCRYPTION_KEY"):
            EncryptedText().process_bind_param("x", None)
    finally:
        get_settings.cache_clear()
