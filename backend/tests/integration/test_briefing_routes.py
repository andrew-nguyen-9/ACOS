"""15.4 — GET /briefing read surface."""
from __future__ import annotations


def test_briefing_returns_all_sections(client):
    resp = client.get("/api/v1/briefing")
    assert resp.status_code == 200
    data = resp.json()
    for section in (
        "jobs_to_apply",
        "skill_gaps",
        "resume_adjustments",
        "ats_opportunities",
        "follow_ups",
        "goal",
        "generated_at",
    ):
        assert section in data
    # Fresh tenant → honest empty sections, never fabricated.
    assert data["jobs_to_apply"] == []
    assert data["goal"] is None
