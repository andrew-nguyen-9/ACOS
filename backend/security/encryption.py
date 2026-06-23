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

import json

from sqlalchemy import Text
from sqlalchemy.types import TypeDecorator

from backend.config import get_settings


def encryption_enabled() -> bool:
    return get_settings().enable_encrypted_storage


def _fernet():
    """Build a Fernet from the active data key, with clear errors when misconfigured.

    16.2 (ADR-015): the key is the unlocked DEK from keymgmt (wrapped by passphrase
    and Keychain), falling back to the 14.3 ``ACOS_ENCRYPTION_KEY`` env key.
    """
    try:
        from cryptography.fernet import Fernet
    except ModuleNotFoundError as exc:  # pragma: no cover - env-dependent
        raise RuntimeError(
            "encrypted storage is enabled but `cryptography` is not installed; "
            "run `pip install -r requirements-encryption.txt`"
        ) from exc
    from backend.security import keymgmt

    key = keymgmt.get_active_key()
    if not key:
        raise RuntimeError(
            "encrypted storage is enabled but no key is unlocked "
            "(unlock via passphrase/Keychain or set ACOS_ENCRYPTION_KEY)"
        )
    return Fernet(key)


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


class EncryptedJSON(TypeDecorator):
    """Like EncryptedText but for a JSON column (e.g. ``Resume.content_json``).

    OFF: stores plain JSON text (byte-identical to a JSON column). ON: stores a
    Fernet token over the serialized JSON. A value that doesn't decrypt is parsed
    as legacy plaintext JSON, so flipping the flag never bricks existing rows.
    """

    impl = Text
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        raw = json.dumps(value)
        if not encryption_enabled():
            return raw
        return _fernet().encrypt(raw.encode()).decode()

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        if encryption_enabled():
            try:
                return json.loads(_fernet().decrypt(value.encode()).decode())
            except Exception:
                pass  # legacy plaintext JSON — fall through
        return json.loads(value)
