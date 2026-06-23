"""Phase 16.2 (ADR-015) — KEK key management: dual-unwrap of one DEK."""
from __future__ import annotations

import pytest

pytest.importorskip("cryptography")

from backend.security import keymgmt


def test_passphrase_and_keychain_unwrap_same_dek(tmp_path):
    kek = keymgmt.new_keychain_kek()
    material, dek = keymgmt.create_key_material("correct horse", kek)

    # Both independent paths recover the *same* data key (the KEK pattern).
    assert keymgmt.unwrap_with_passphrase(material, "correct horse") == dek
    assert keymgmt.unwrap_with_keychain(material, kek) == dek


def test_wrong_passphrase_fails(tmp_path):
    kek = keymgmt.new_keychain_kek()
    material, _ = keymgmt.create_key_material("right", kek)
    with pytest.raises(Exception):
        keymgmt.unwrap_with_passphrase(material, "wrong")


def test_material_persists_no_bare_dek(tmp_path):
    kek = keymgmt.new_keychain_kek()
    material, dek = keymgmt.create_key_material("pw", kek)
    path = tmp_path / "keyfile.json"
    keymgmt.save_material(material, path)

    raw = path.read_text()
    assert dek.decode() not in raw  # the keyfile never holds the bare DEK
    loaded = keymgmt.load_material(path)
    assert loaded is not None
    assert keymgmt.unwrap_with_passphrase(loaded, "pw") == dek


def test_load_missing_returns_none(tmp_path):
    assert keymgmt.load_material(tmp_path / "absent.json") is None


def test_active_key_falls_back_to_env(monkeypatch):
    keymgmt.set_active_key(None)
    monkeypatch.setenv("ACOS_ENCRYPTION_KEY", "env-key")
    assert keymgmt.get_active_key() == b"env-key"
    keymgmt.set_active_key(b"unlocked")
    assert keymgmt.get_active_key() == b"unlocked"  # unlocked DEK wins
    keymgmt.set_active_key(None)
