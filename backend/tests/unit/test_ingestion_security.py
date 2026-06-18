import hashlib
import os
import tempfile
import pytest
from pathlib import Path
from backend.ingestion.security import validate_path, validate_size, compute_checksum


@pytest.fixture
def tmp_allowed(tmp_path):
    return str(tmp_path)


def test_validate_path_within_allowlist(tmp_allowed, tmp_path):
    f = tmp_path / "resume.txt"
    f.write_text("hello")
    result = validate_path(str(f), [tmp_allowed])
    assert result == f.resolve()


def test_validate_path_traversal_rejected(tmp_allowed, tmp_path):
    with pytest.raises(ValueError, match="not under any allowed"):
        validate_path("/etc/passwd", [tmp_allowed])


def test_validate_path_dotdot_rejected(tmp_allowed, tmp_path):
    evil = str(tmp_path / ".." / "etc" / "passwd")
    with pytest.raises(ValueError, match="not under any allowed"):
        validate_path(evil, [tmp_allowed])


def test_validate_size_passes_small_file(tmp_path):
    f = tmp_path / "small.txt"
    f.write_bytes(b"x" * 100)
    validate_size(f)  # Should not raise


def test_validate_size_rejects_large_file(tmp_path):
    f = tmp_path / "big.txt"
    f.write_bytes(b"x" * (52_428_800 + 1))
    with pytest.raises(ValueError, match="exceeds"):
        validate_size(f)


def test_compute_checksum(tmp_path):
    f = tmp_path / "data.txt"
    content = b"hello world"
    f.write_bytes(content)
    expected = hashlib.sha256(content).hexdigest()
    assert compute_checksum(f) == expected
