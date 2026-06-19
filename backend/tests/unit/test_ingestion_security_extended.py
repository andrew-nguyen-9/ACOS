from __future__ import annotations

import pytest
from backend.ingestion.security import sanitize_filename, validate_path, compute_checksum


def test_sanitize_filename_strips_path_separators():
    assert sanitize_filename("../../../etc/passwd") == "passwd"


def test_sanitize_filename_strips_forward_slash():
    assert sanitize_filename("/tmp/evil/file.txt") == "file.txt"


def test_sanitize_filename_keeps_safe_name():
    assert sanitize_filename("resume.pdf") == "resume.pdf"


def test_sanitize_filename_replaces_empty_with_upload():
    assert sanitize_filename("") == "upload"


def test_sanitize_filename_replaces_dot_with_upload():
    assert sanitize_filename(".") == "upload"


def test_sanitize_filename_replaces_dotdot_with_upload():
    assert sanitize_filename("..") == "upload"


def test_sanitize_filename_replaces_none_with_upload():
    assert sanitize_filename(None) == "upload"  # type: ignore[arg-type]


def test_validate_path_symlink_outside_allowlist_rejected(tmp_path):
    """A symlink that resolves outside the allowlist must be rejected."""
    outside = tmp_path / "outside"
    outside.mkdir()
    target_file = outside / "secret.txt"
    target_file.write_text("secret")

    inside = tmp_path / "allowed"
    inside.mkdir()
    link = inside / "link.txt"
    link.symlink_to(target_file)

    # The resolved target is outside "allowed/" so it must be rejected
    with pytest.raises(ValueError, match="not under any allowed"):
        validate_path(str(link), [str(inside)])


def test_compute_checksum_deterministic(tmp_path):
    f = tmp_path / "data.bin"
    f.write_bytes(b"\x00\xff\xab\xcd" * 1000)
    c1 = compute_checksum(f)
    c2 = compute_checksum(f)
    assert c1 == c2
    assert len(c1) == 64  # SHA-256 hex
