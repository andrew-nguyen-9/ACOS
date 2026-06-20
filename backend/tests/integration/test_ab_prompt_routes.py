import pytest
from backend.database import seed_system_config


@pytest.fixture
def seeded(test_session):
    seed_system_config(test_session)
    test_session.commit()


def test_ab_experiment_lifecycle(client, seeded):
    create = client.post("/api/v1/optimization/experiments", json={
        "name": "Resume A/B", "target_engine": "resume",
        "variant_a": {"template": "software"}, "variant_b": {"template": "modern"},
    })
    assert create.status_code == 200, create.text
    ids = create.json()["variant_ids"]
    a, b = ids["A"], ids["B"]

    # conclude with no data → 409
    exp_id = create.json()["experiment_id"]
    assert client.post(f"/api/v1/optimization/experiments/{exp_id}/conclude").status_code == 409

    for _ in range(3):
        client.post(f"/api/v1/optimization/experiments/variants/{a}/impression")
        client.post(f"/api/v1/optimization/experiments/variants/{b}/impression")
    client.post(f"/api/v1/optimization/experiments/variants/{b}/conversion")
    client.post(f"/api/v1/optimization/experiments/variants/{b}/conversion")

    concluded = client.post(f"/api/v1/optimization/experiments/{exp_id}/conclude")
    assert concluded.status_code == 200
    assert concluded.json()["winner_variant_id"] == b

    listing = client.get("/api/v1/optimization/experiments")
    assert listing.status_code == 200
    assert listing.json()["experiments"][0]["status"] == "concluded"


def test_prompt_seed_and_activate(client, seeded):
    seed = client.post("/api/v1/optimization/prompts/resume/generate/seed")
    assert seed.status_code == 200, seed.text
    assert seed.json()["is_active"] is True

    versions = client.get("/api/v1/optimization/prompts/resume/generate/versions")
    assert versions.status_code == 200
    vid = versions.json()["versions"][0]["id"]

    activate = client.post(f"/api/v1/optimization/prompts/versions/{vid}/activate")
    assert activate.status_code == 200
    assert activate.json()["is_active"] is True
