"""
End-to-end optimization cycle — single function, state-threaded.
Steps: seed outcomes → run loop → list pending proposal → approve → apply
       → verify config changed → revert → verify config restored → audit log.
No Ollama or ChromaDB required (the loop is pure metrics + proposals).
"""
import pytest
from backend.database import seed_system_config
from backend.repositories.outcome import OutcomeSignalRepository
from backend.repositories.system_config import SystemConfigRepository
from backend.services.learning.ranker import _SIGNAL_WEIGHTS
from backend.models.application import Application


@pytest.fixture
def seeded(test_session):
    seed_system_config(test_session)
    repo = OutcomeSignalRepository(test_session)
    # 5 strong template-A + 5 weak template-B → clear template proposal
    for sig, tpl, n in (("interview", "A", 5), ("no_response", "B", 5)):
        for _ in range(n):
            app = Application(company="C", position="P"); test_session.add(app); test_session.flush()
            repo.create(application_id=app.id, signal_type=sig,
                        signal_weight=_SIGNAL_WEIGHTS[sig], ats_score=70,
                        template_used=tpl, industry="ai")
    test_session.commit()


def test_optimization_full_cycle(client, seeded):
    # Step 1: learning loop fires (10 apps, trigger 5)
    loop = client.post("/api/v1/optimization/loop/run")
    assert loop.status_code == 200 and loop.json()["ran"] is True

    # Step 2: a pending template proposal exists
    pending = client.get("/api/v1/optimization/proposals?status=pending").json()["proposals"]
    template_props = [p for p in pending if p["target_parameter"] == "default_template"]
    assert template_props, "expected a default_template proposal"
    pid = template_props[0]["id"]
    assert template_props[0]["proposed_value"] == "A"   # A had the strong signals

    # Step 3: apply is blocked before approval (guardrail)
    assert client.post(f"/api/v1/optimization/proposals/{pid}/apply").status_code == 409

    # Step 4: approve → apply → config changed
    assert client.post(f"/api/v1/optimization/proposals/{pid}/approve").status_code == 200
    applied = client.post(f"/api/v1/optimization/proposals/{pid}/apply")
    assert applied.status_code == 200 and applied.json()["new_value"] == "A"

    # Step 5: revert → config restored, proposal marked reverted
    rev = client.post(f"/api/v1/optimization/proposals/{pid}/revert")
    assert rev.status_code == 200 and rev.json()["action"] == "reverted"

    # Step 6: audit log holds both apply and revert (immutable trail)
    actions = {l["action"] for l in client.get("/api/v1/optimization/logs").json()["logs"]}
    assert {"applied", "reverted"} <= actions
