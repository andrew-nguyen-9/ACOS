"""Optional at-rest field encryption (Phase 14.3, ADR-013).

**OFF by default.** Honest threat model: this protects against *local-disk theft*
as defense-in-depth over macOS FileVault. It is **not** a multi-user, network, or
in-memory boundary — the key lives on the same machine, and a running app holds
plaintext. Don't oversell it (CLAUDE.md #1).

Enable by installing the extra (`pip install -r requirements-encryption.txt`),
setting ``ACOS_ENABLE_ENCRYPTED_STORAGE=1`` and providing ``ACOS_ENCRYPTION_KEY``
(a urlsafe-base64 Fernet key; production should source it from the OS keychain).

Uses Fernet — authenticated symmetric encryption from `cryptography` (context7:
the maintained, reviewed primitive). No custom cipher.
"""
from __future__ import annotations

import os

from sqlalchemy import Text
from sqlalchemy.types import TypeDecorator

from backend.config import get_settings


def encryption_enabled() -> bool:
    return get_settings().enable_encrypted_storage


def _fernet():
    """Build a Fernet from the env key, with clear errors when misconfigured."""
    try:
        from cryptography.fernet import Fernet
    except ModuleNotFoundError as exc:  # pragma: no cover - env-dependent
        raise RuntimeError(
            "encrypted storage is enabled but `cryptography` is not installed; "
            "run `pip install -r requirements-encryption.txt`"
        ) from exc
    key = os.environ.get("ACOS_ENCRYPTION_KEY")
    if not key:
        raise RuntimeError(
            "encrypted storage is enabled but ACOS_ENCRYPTION_KEY is not set"
        )
    return Fernet(key.encode() if isinstance(key, str) else key)


class EncryptedText(TypeDecorator):
    """A Text column transparently encrypted at rest when the flag is on.

    - **OFF (default):** pure passthrough — the stored bytes are byte-identical to
      a plain ``Text`` column, so toggling the feature changes nothing for users
      who never enable it.
    - **ON:** new writes are Fernet tokens; reads decrypt. A value that does not
      decrypt is returned as-is — that's a row written as plaintext *before* the
      flag was flipped, so enabling encryption never bricks existing data.

    # ponytail: one-way migration in practice — encrypt-in-place of old rows is a
    # batch job, not built here; turning the flag back OFF after writing tokens
    # would surface ciphertext on read (documented, not silently handled).
    """

    impl = Text
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None or not encryption_enabled():
            return value
        return _fernet().encrypt(value.encode()).decode()

    def process_result_value(self, value, dialect):
        if value is None or not encryption_enabled():
            return value
        try:
            return _fernet().decrypt(value.encode()).decode()
        except Exception:
            return value  # legacy plaintext, or not a token — return unchanged
