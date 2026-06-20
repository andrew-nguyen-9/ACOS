from backend.database import seed_system_config


def test_get_settings_returns_seeded_defaults(client, test_session):
    seed_system_config(test_session)
    test_session.commit()
    resp = client.get("/api/v1/settings")
    assert resp.status_code == 200
    data = resp.json()
    assert "settings" in data
    assert "default_model" in data["settings"]
    assert "github_username" in data["settings"]


def test_update_known_setting(client, test_session):
    seed_system_config(test_session)
    test_session.commit()
    resp = client.put("/api/v1/settings/default_model", json={"value": "llama3:8b"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["key"] == "default_model"
    assert body["value"] == "llama3:8b"


def test_update_unknown_setting_returns_404(client, test_session):
    seed_system_config(test_session)
    test_session.commit()
    resp = client.put("/api/v1/settings/nonexistent_key_xyz", json={"value": "x"})
    assert resp.status_code == 404


def test_onboarding_status_initial_is_false(client, test_session):
    seed_system_config(test_session)
    test_session.commit()
    resp = client.get("/api/v1/settings/onboarding")
    assert resp.status_code == 200
    assert resp.json()["completed"] is False


def test_complete_onboarding_persists(client, test_session):
    seed_system_config(test_session)
    test_session.commit()
    resp = client.post("/api/v1/settings/onboarding/complete")
    assert resp.status_code == 200
    assert resp.json()["completed"] is True
    resp2 = client.get("/api/v1/settings/onboarding")
    assert resp2.json()["completed"] is True
