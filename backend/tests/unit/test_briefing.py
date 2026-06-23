"""15.4 — daily briefing orchestrator: composes existing engines, recommend-only."""
from __future__ import annotations

from pathlib import Path

from backend.repositories.application import ApplicationRepository
from backend.services.briefing.service import BriefingService

_JD = (
    "Senior Data Analyst. Python and SQL required. Build ETL pipelines, maintain "
    "Tableau dashboards, define KPIs for executive stakeholders. Data analytics role."
)


def _add_app(session, **kw) -> None:
    repo = ApplicationRepository(session)
    defaults = dict(company="Acme", position="Analyst", status="draft")
    defaults.update(kw)
    repo.create(**defaults)
    session.flush()


def test_compose_returns_all_five_sections(test_session) -> None:
    briefing = BriefingService(test_session).compose()
    for section in (
        "jobs_to_apply",
        "skill_gaps",
        "resume_adjustments",
        "ats_opportunities",
        "follow_ups",
        "goal",
        "generated_at",
    ):
        assert section in briefing


def test_empty_inputs_yield_honest_empty_sections(test_session) -> None:
    # A fresh user with no applications/signals gets empty sections, never invented data.
    briefing = BriefingService(test_session).compose()
    assert briefing["jobs_to_apply"] == []
    assert briefing["ats_opportunities"] == []
    assert briefing["follow_ups"] == []
    assert briefing["goal"] is None  # no outcome signals → no fabricated goal


def test_jobs_and_followups_compose_from_real_applications(test_session) -> None:
    _add_app(test_session, company="DataCo", position="Analyst", status="draft", job_description=_JD)
    _add_app(test_session, company="LiveCo", position="PM", status="interview")
    briefing = BriefingService(test_session).compose()

    # The draft-with-JD is an ATS opportunity; the interview app is a follow-up.
    assert any(o["company"] == "DataCo" for o in briefing["ats_opportunities"])
    assert any(f["company"] == "LiveCo" and f["status"] == "interview" for f in briefing["follow_ups"])
    # Every surfaced job carries an explicit goal-alignment flag (not decorative).
    for job in briefing["jobs_to_apply"]:
        assert "aligned_to_goal" in job
        assert "confidence" in job


def test_briefing_is_off_the_hot_path() -> None:
    # Trap 1: the briefing must not be imported by any generation path, so it adds
    # zero per-request latency. Scan the generation services for a briefing import.
    backend = Path(__file__).resolve().parents[2]
    gen_paths = [
        "services/resume/generator.py",
        "services/cover_letter/generator.py",
        "services/copilot",
    ]
    for rel in gen_paths:
        p = backend / rel
        files = p.rglob("*.py") if p.is_dir() else [p]
        for f in files:
            if f.exists():
                assert "briefing" not in f.read_text().lower(), (
                    f"{f} imports the briefing on a generation path — it must stay off the hot path"
                )
