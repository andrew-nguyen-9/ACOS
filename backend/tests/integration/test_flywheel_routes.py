"""Phase 12.11 read-only flywheel ROI endpoint."""
from __future__ import annotations

from backend.services.flywheel.feedback import FeedbackEngine


def _seed(session) -> None:
    eng = FeedbackEngine(session)
    outcomes = [("app1", "interview", 0.7), ("app2", "offer", 1.0),
                ("app3", "rejected", 0.1), ("app4", "interview", 0.7),
                ("app5", "phone_screen", 0.4), ("app6", "final_round", 0.85),
                ("app7", "no_response", 0.0)]  # not python — pulls global mean below python's
    for app_id, stype, w in outcomes:
        eng.record_signal(entity_type="application", entity_id=app_id, signal_type=stype,
                          value=w, source={"table": "outcome_signals", "ids": [f"os-{app_id}"]})
    for app_id in [o[0] for o in outcomes[:6]]:  # python in app1..app6 only
        eng.record_signal(entity_type="skill", entity_id="python", signal_type="skill_used",
                          value=1.0, source={"table": "resumes", "ids": [app_id]})


def test_skills_roi_endpoint_returns_ranked_recommended(client, test_session):
    _seed(test_session)
    resp = client.get("/api/v1/flywheel/skills/roi?metric=interview_lift&min_n=5")
    assert resp.status_code == 200
    data = resp.json()
    assert data["metric"] == "interview_lift"
    assert data["recommended"] == ["python"]
    assert data["skills"][0]["skill"] == "python"
    assert data["skills"][0]["confidence"] == "strong_inference"


def test_skills_roi_endpoint_rejects_unknown_metric(client):
    resp = client.get("/api/v1/flywheel/skills/roi?metric=bogus")
    assert resp.status_code == 422


def test_prompt_versions_endpoint_returns_lineage(client, test_session):
    """13.4: GET read side backing the prompt-review queue."""
    from backend.services.flywheel.prompt_evolution import PromptEvolutionService
    from backend.services.prompts.registry import PromptRegistry

    PromptRegistry(test_session).deploy("resume/extract_keywords", "system: v1", version="v1")
    PromptEvolutionService(test_session).propose(
        "resume/extract_keywords", "system: v2", signal_ids=["sigZ"],
        rationale="v1 weak", expected_impact="lift",
    )

    resp = client.get("/api/v1/flywheel/prompt/versions?prompt_name=resume/extract_keywords")
    assert resp.status_code == 200
    data = resp.json()
    assert data["prompt_name"] == "resume/extract_keywords"
    assert data["active_version"] == "v1"               # candidate did NOT auto-activate
    assert [v["version"] for v in data["versions"]] == ["v1", "v2"]
    assert any("sigZ" in (v["change_rationale"] or "") for v in data["versions"])
