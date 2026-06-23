"""ADR-012 — the controlled-autonomy boundary, enforced by absence.

Mirrors ADR-010's never-promote test: the agent surfaces may rank / recommend /
generate / simulate, but there must be NO code path that submits an application,
contacts a recruiter, or mutates an external system on the user's behalf. This
test scans the agent-surface modules for outbound-action capabilities and fails
the moment one is introduced.

The list of surfaces grows as Phase 15 lands (15.2 suggestion, 15.3 interview
sim, 15.4 briefing) — each new agent surface registers here.
"""
from __future__ import annotations

from pathlib import Path

import pytest

_BACKEND = Path(__file__).resolve().parents[2]

# Agent-surface modules whose code must contain no outbound-action path.
_SURFACES = [
    "services/strategy/application_strategy.py",
    "services/strategy/application_suggestion.py",
    "api/v1/routes/strategy.py",
]

# Symbols/idioms that would constitute acting on an external system on the user's
# behalf. Inbound reads (HTTP GET scraping public JDs for the corpus) are allowed;
# these are submit/contact/mutate semantics only.
_FORBIDDEN = [
    "requests.post",
    "requests.put",
    "requests.patch",
    "httpx.post",
    "httpx.put",
    "httpx.patch",
    "smtplib",
    "submit_application",
    "post_application",
    "apply_to_job",
    "contact_recruiter",
    "send_email",
    "send_message",
    "send_outreach",
]


@pytest.mark.parametrize("rel", _SURFACES)
def test_agent_surface_has_no_outbound_action_path(rel: str) -> None:
    path = _BACKEND / rel
    assert path.exists(), f"agent surface missing: {rel}"
    src = path.read_text()
    hits = [tok for tok in _FORBIDDEN if tok in src]
    assert not hits, (
        f"ADR-012 boundary violated in {rel}: outbound-action token(s) {hits}. "
        "The agent recommends, it never acts. Remove the external action path."
    )
