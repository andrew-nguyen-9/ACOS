import pytest
from backend.database import seed_system_config
from backend.repositories.outcome import OutcomeSignalRepository
from backend.services.learning.ranker import _SIGNAL_WEIGHTS
from backend.models.application import Application


@pytest.fixture
def seeded(test_session):
    seed_system_config(test_session)
    repo = OutcomeSignalRepository(test_session)
    # 5 strong (template A) + 5 weak (template B) → template proposal
    for sig, tpl, n in (("interview", "A", 5), ("no_response", "B", 5)):
        for _ in range(n):
            app = Application(company="C", position="P"); test_session.add(app); test_session.flush()
            repo.create(application_id=app.id, signal_type=sig,
                        signal_weight=_SIGNAL_WEIGHTS[sig], ats_score=70,
                        template_used=tpl, industry="ai")
    test_session.commit()


def test_generate_list_approve_apply_revert(client, seeded):
    gen = client.post("/api/v1/optimization/proposals/generate")
    assert gen.status_code == 200, gen.text
    assert gen.json()["created"] >= 1

    listing = client.get("/api/v1/optimization/proposals?status=pending")
    assert listing.status_code == 200
    proposals = listing.json()["proposals"]
    pid = proposals[0]["id"]

    # apply before approve → 409
    early = client.post(f"/api/v1/optimization/proposals/{pid}/apply")
    assert early.status_code == 409

    assert client.post(f"/api/v1/optimization/proposals/{pid}/approve").status_code == 200
    applied = client.post(f"/api/v1/optimization/proposals/{pid}/apply")
    assert applied.status_code == 200
    assert applied.json()["action"] == "applied"

    reverted = client.post(f"/api/v1/optimization/proposals/{pid}/revert")
    assert reverted.status_code == 200
    assert reverted.json()["action"] == "reverted"

    logs = client.get("/api/v1/optimization/logs")
    assert logs.status_code == 200
    assert len(logs.json()["logs"]) >= 2


def test_reject_then_apply_blocked(client, seeded):
    client.post("/api/v1/optimization/proposals/generate")
    pid = client.get("/api/v1/optimization/proposals").json()["proposals"][0]["id"]
    assert client.post(f"/api/v1/optimization/proposals/{pid}/reject").status_code == 200
    assert client.post(f"/api/v1/optimization/proposals/{pid}/apply").status_code == 409


def test_loop_run_endpoint(client, seeded):
    out = client.post("/api/v1/optimization/loop/run")
    assert out.status_code == 200
    assert out.json()["ran"] is True
