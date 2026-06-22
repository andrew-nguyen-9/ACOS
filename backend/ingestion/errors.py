"""Ingestion error taxonomy (Phase 11.1).

Distinguishes retryable failures (file locks, parser hiccups) from permanent
ones (unsupported type, validation failure) so the retry helper only re-runs
work that might actually succeed on a second attempt.
"""
from __future__ import annotations


class IngestionError(Exception):
    """Base for ingestion failures."""


class TransientError(IngestionError):
    """Retryable: a transient condition (file lock, flaky parser, I/O blip)."""


class PermanentError(IngestionError):
    """Not retryable: re-running will fail the same way (bad input, validation)."""
