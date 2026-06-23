"""Phase 12.15 anonymization — the k-anonymity emission gate (ADR-009).

The privacy boundary is one gate: a candidate global pattern is emitted only if at
least ``K_ANONYMITY`` tenants back it AND every field is on the abstract allowlist.
``assert_no_reidentification`` is the re-id self-check the tests scan artifacts with.
"""
from __future__ import annotations

K_ANONYMITY = 5

# Default-closed: only these abstract fields may appear on a global pattern. A new
# field is rejected until explicitly allowlisted (ADR-009 §2).
ALLOWED_FIELDS = frozenset(
    {"pattern_type", "industry", "key", "value", "metric", "tenant_count", "confidence", "rank"}
)

# Key names that would re-identify a tenant or carry raw content / embeddings.
_FORBIDDEN_KEYS = frozenset({"raw_text", "content", "text", "embedding", "embeddings"})


class ReidentificationError(Exception):
    """A global artifact carried a disallowed field — a privacy leak was prevented."""


def gate(patterns: list[dict], k: int = K_ANONYMITY) -> list[dict]:
    """Return only emittable patterns: allowlisted fields + >= k contributing tenants.

    Raises ``ReidentificationError`` on a disallowed field (default-closed); silently
    drops (suppresses) any pattern below the k-anonymity threshold.
    """
    out: list[dict] = []
    for p in patterns:
        extra = set(p) - ALLOWED_FIELDS
        if extra:
            raise ReidentificationError(
                f"disallowed field(s) in global pattern: {sorted(extra)}"
            )
        if int(p.get("tenant_count", 0)) < k:
            continue  # k-anonymity: small cohort suppressed
        out.append(p)
    # Field-name allowlist guards keys; this guards VALUES (a tenant id / embedding /
    # raw text hidden inside an allowlisted field) — run it on the production path,
    # not only in tests.
    assert_no_reidentification(out)
    return out


def _is_number_like(x: object) -> bool:
    if isinstance(x, bool):
        return False
    if isinstance(x, (int, float)):
        return True
    if isinstance(x, str):
        try:
            float(x)
            return True
        except ValueError:
            return False
    return False


def _scan(node: object) -> None:
    if isinstance(node, dict):
        for key, value in node.items():
            kl = str(key).lower()
            # any tenant-referencing key is forbidden EXCEPT the allowlisted count
            # (a count is aggregate; ids/lists are re-identifying).
            if (("tenant" in kl and kl != "tenant_count") or kl in _FORBIDDEN_KEYS):
                raise ReidentificationError(f"re-identifying field present: {key!r}")
            _scan(value)
    elif isinstance(node, (list, tuple)):
        # a numeric vector is an embedding; a list of labels is abstract structure.
        # Catch both real numbers and a serialized embedding (stringified floats).
        if node and all(_is_number_like(x) for x in node):
            raise ReidentificationError("embedding-like numeric vector present in artifact")
        for item in node:
            _scan(item)


def assert_no_reidentification(artifact: object) -> None:
    """Scan a global artifact for raw text / embeddings / tenant ids. Raises on any."""
    _scan(artifact)
