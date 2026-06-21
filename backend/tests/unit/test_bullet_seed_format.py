"""Validate bullet_training_data.py: count, shape, constraints."""
from __future__ import annotations

import pytest
from scripts.seed.bullet_training_data import BULLET_EXAMPLES

_VALID_ROLE_TYPES = {
    "product_management", "data_analytics", "consulting", "engineering", "tpm_solutions"
}
_VALID_DIMENSIONS = {
    "impact", "leadership", "technical", "strategic", "cross_functional"
}


def test_count():
    assert len(BULLET_EXAMPLES) == 500


def test_each_has_required_keys():
    required = {"text", "role_type", "dimension", "verb", "has_metric"}
    for i, b in enumerate(BULLET_EXAMPLES):
        assert required == set(b.keys()), f"Bullet {i} missing keys"


def test_role_types_valid():
    for i, b in enumerate(BULLET_EXAMPLES):
        assert b["role_type"] in _VALID_ROLE_TYPES, f"Bullet {i} bad role_type: {b['role_type']}"


def test_dimensions_valid():
    for i, b in enumerate(BULLET_EXAMPLES):
        assert b["dimension"] in _VALID_DIMENSIONS, f"Bullet {i} bad dimension: {b['dimension']}"


def test_has_metric_bool():
    for i, b in enumerate(BULLET_EXAMPLES):
        assert isinstance(b["has_metric"], bool), f"Bullet {i} has_metric not bool"


def test_text_length():
    for i, b in enumerate(BULLET_EXAMPLES):
        assert 20 <= len(b["text"]) <= 250, f"Bullet {i} text length out of range: {len(b['text'])}"


def test_text_not_empty():
    for i, b in enumerate(BULLET_EXAMPLES):
        assert b["text"].strip(), f"Bullet {i} text is blank"


def test_verb_not_empty():
    for i, b in enumerate(BULLET_EXAMPLES):
        assert b["verb"].strip(), f"Bullet {i} verb is blank"


def test_min_per_role_type():
    from collections import Counter
    counts = Counter(b["role_type"] for b in BULLET_EXAMPLES)
    for rt in _VALID_ROLE_TYPES:
        assert counts[rt] >= 90, f"{rt} has only {counts[rt]} bullets (min 90)"


def test_each_role_has_all_dimensions():
    from collections import defaultdict
    by_role: dict[str, set[str]] = defaultdict(set)
    for b in BULLET_EXAMPLES:
        by_role[b["role_type"]].add(b["dimension"])
    for rt, dims in by_role.items():
        assert dims == _VALID_DIMENSIONS, f"{rt} missing dimensions: {_VALID_DIMENSIONS - dims}"


def test_metric_ratio_sane():
    with_metric = sum(1 for b in BULLET_EXAMPLES if b["has_metric"])
    ratio = with_metric / len(BULLET_EXAMPLES)
    # Expect roughly 70-90% of bullets to have metrics
    assert 0.60 <= ratio <= 0.95, f"has_metric ratio unexpected: {ratio:.2f}"
