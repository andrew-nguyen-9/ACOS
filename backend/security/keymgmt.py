"""Phase 16.2 (ADR-015) — encryption key management (the KEK pattern).

One random **data-encryption key** (DEK) encrypts every field (via
``EncryptedText``/``EncryptedJSON``). The DEK is never stored bare — it is *wrapped*
two independent ways, either of which unlocks it (ADR-015 §2):

  - **passphrase → scrypt KDF → Fernet KEK** wraps the DEK. Portable; survives a
    machine migration; works if the Keychain is unavailable.
  - **Keychain-stored random KEK** wraps the same DEK (ADR-014 trust root) for
    frictionless unlock on the enrolled machine.

Rotating either wrap never re-encrypts the data — only the small wrapped-DEK blob
changes. The key material (salt + the two wrapped blobs, NEVER the DEK) lives in a
keyfile beside the DB.

Honest threat model (ADR-015 §3): this defends disk theft / file exfiltration while
locked. It is NOT a runtime or multi-user boundary — a running process holds the
DEK in memory; that boundary is auth's job (ADR-014). No passphrase recovery
(ADR-001): lose it and, with encryption on, the data is gone.

stdlib scrypt is the KDF (no new dep; same as 16.1 auth). Fernet (cryptography,
the 14.3 optional extra) is the wrapping cipher.
"""
from __future__ import annotations

import base64
import json
import os
import secrets
from dataclasses import dataclass
from pathlib import Path

_SCRYPT_N = 2**14
_SCRYPT_R = 8
_SCRYPT_P = 1

# Process-global unlocked DEK. EncryptedText reads it; None → fall back to the
# ACOS_ENCRYPTION_KEY env key (14.3 backward-compat) or no encryption.
_active_dek: bytes | None = None


def _fernet(key: bytes):
    from cryptography.fernet import Fernet

    return Fernet(key)


def _kek_from_passphrase(passphrase: str, salt: bytes) -> bytes:
    import hashlib

    dk = hashlib.scrypt(
        passphrase.encode("utf-8"), salt=salt, n=_SCRYPT_N, r=_SCRYPT_R, p=_SCRYPT_P, dklen=32
    )
    return base64.urlsafe_b64encode(dk)  # Fernet wants urlsafe-b64 32-byte key


@dataclass
class KeyMaterial:
    """Non-secret wrapped key material safe to persist (no bare DEK)."""

    salt: str  # b64
    kdf_wrapped: str  # Fernet token: KEK(passphrase) over DEK
    keychain_wrapped: str  # Fernet token: keychain KEK over DEK

    def to_json(self) -> str:
        return json.dumps(
            {"salt": self.salt, "kdf_wrapped": self.kdf_wrapped,
             "keychain_wrapped": self.keychain_wrapped}
        )

    @staticmethod
    def from_json(raw: str) -> "KeyMaterial":
        d = json.loads(raw)
        return KeyMaterial(d["salt"], d["kdf_wrapped"], d["keychain_wrapped"])


def new_keychain_kek() -> bytes:
    """A random Fernet key to be stowed in the OS Keychain (the keychain-wrap side)."""
    return base64.urlsafe_b64encode(secrets.token_bytes(32))


def create_key_material(passphrase: str, keychain_kek: bytes) -> tuple[KeyMaterial, bytes]:
    """Generate a fresh DEK and wrap it both ways. Returns (material, dek).

    Persist the material; hand the DEK to ``set_active_key`` (and the keychain_kek
    to the OS Keychain via the 16.1 commands). The DEK itself is never written.
    """
    dek = base64.urlsafe_b64encode(secrets.token_bytes(32))  # the data key (also a Fernet key)
    salt = secrets.token_bytes(16)
    kdf_kek = _kek_from_passphrase(passphrase, salt)
    return (
        KeyMaterial(
            salt=base64.b64encode(salt).decode(),
            kdf_wrapped=_fernet(kdf_kek).encrypt(dek).decode(),
            keychain_wrapped=_fernet(keychain_kek).encrypt(dek).decode(),
        ),
        dek,
    )


def unwrap_with_passphrase(material: KeyMaterial, passphrase: str) -> bytes:
    """Recover the DEK via the passphrase path. Raises on a wrong passphrase."""
    kek = _kek_from_passphrase(passphrase, base64.b64decode(material.salt))
    return _fernet(kek).decrypt(material.kdf_wrapped.encode())


def unwrap_with_keychain(material: KeyMaterial, keychain_kek: bytes) -> bytes:
    """Recover the DEK via the Keychain path."""
    return _fernet(keychain_kek).decrypt(material.keychain_wrapped.encode())


# ── persistence ──────────────────────────────────────────────────────────────

def keyfile_path() -> Path:
    from backend.config import get_settings

    return Path(get_settings().db_path).parent / "keyfile.json"


def save_material(material: KeyMaterial, path: Path | None = None) -> None:
    p = path or keyfile_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(material.to_json())


def load_material(path: Path | None = None) -> KeyMaterial | None:
    p = path or keyfile_path()
    if not p.exists():
        return None
    return KeyMaterial.from_json(p.read_text())


# ── active-key state (read by EncryptedText) ─────────────────────────────────

def set_active_key(dek: bytes | None) -> None:
    global _active_dek
    _active_dek = dek


def get_active_key() -> bytes | None:
    """The unlocked DEK, or the env key (14.3 path) if no DEK is unlocked."""
    if _active_dek is not None:
        return _active_dek
    env = os.environ.get("ACOS_ENCRYPTION_KEY")
    return env.encode() if env else None
