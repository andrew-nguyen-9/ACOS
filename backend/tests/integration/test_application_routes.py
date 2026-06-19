from __future__ import annotations


def test_create_application(client):
    resp = client.post("/api/v1/applications", json={"company": "Acme", "position": "Engineer"})
    assert resp.status_code == 201
    data = resp.json()
    assert data["company"] == "Acme"
    assert data["status"] == "draft"
    assert "id" in data
    assert "created_at" in data


def test_list_applications_empty(client):
    resp = client.get("/api/v1/applications")
    assert resp.status_code == 200
    assert resp.json() == []


def test_list_applications_filter_by_status(client):
    client.post("/api/v1/applications", json={"company": "A", "position": "P1", "status": "applied"})
    client.post("/api/v1/applications", json={"company": "B", "position": "P2", "status": "draft"})
    resp = client.get("/api/v1/applications?status=applied")
    assert resp.status_code == 200
    result = resp.json()
    assert len(result) == 1
    assert result[0]["company"] == "A"


def test_get_application(client):
    create = client.post("/api/v1/applications", json={"company": "Z", "position": "Dev"})
    app_id = create.json()["id"]
    resp = client.get(f"/api/v1/applications/{app_id}")
    assert resp.status_code == 200
    assert resp.json()["id"] == app_id
    assert resp.json()["company"] == "Z"


def test_get_application_not_found(client):
    resp = client.get("/api/v1/applications/doesnotexist")
    assert resp.status_code == 404


def test_update_status(client):
    create = client.post("/api/v1/applications", json={"company": "X", "position": "Y"})
    app_id = create.json()["id"]
    resp = client.patch(f"/api/v1/applications/{app_id}/status", json={"status": "applied"})
    assert resp.status_code == 200
    assert resp.json()["status"] == "applied"


def test_update_status_invalid(client):
    create = client.post("/api/v1/applications", json={"company": "X", "position": "Y"})
    app_id = create.json()["id"]
    resp = client.patch(f"/api/v1/applications/{app_id}/status", json={"status": "hired"})
    assert resp.status_code == 422


def test_update_status_not_found(client):
    resp = client.patch("/api/v1/applications/doesnotexist/status", json={"status": "applied"})
    assert resp.status_code == 404


def test_add_note(client):
    create = client.post("/api/v1/applications", json={"company": "X", "position": "Y"})
    app_id = create.json()["id"]
    resp = client.post(f"/api/v1/applications/{app_id}/notes", json={"note": "Looks promising"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["event_type"] == "note_added"
    assert data["note"] == "Looks promising"


def test_add_note_not_found(client):
    resp = client.post("/api/v1/applications/doesnotexist/notes", json={"note": "test"})
    assert resp.status_code == 404


def test_get_timeline(client):
    create = client.post("/api/v1/applications", json={"company": "X", "position": "Y"})
    app_id = create.json()["id"]
    client.patch(f"/api/v1/applications/{app_id}/status", json={"status": "applied"})
    resp = client.get(f"/api/v1/applications/{app_id}/timeline")
    assert resp.status_code == 200
    events = resp.json()
    assert any(e["event_type"] == "status_change" for e in events)
    assert any(e["to_status"] == "applied" for e in events)


def test_get_timeline_not_found(client):
    resp = client.get("/api/v1/applications/doesnotexist/timeline")
    assert resp.status_code == 404


def test_delete_application(client):
    create = client.post("/api/v1/applications", json={"company": "X", "position": "Y"})
    app_id = create.json()["id"]
    resp = client.delete(f"/api/v1/applications/{app_id}")
    assert resp.status_code == 204
    assert client.get(f"/api/v1/applications/{app_id}").status_code == 404


def test_delete_application_not_found(client):
    resp = client.delete("/api/v1/applications/doesnotexist")
    assert resp.status_code == 404


def test_create_application_invalid_status(client):
    resp = client.post("/api/v1/applications", json={"company": "A", "position": "B", "status": "hired"})
    assert resp.status_code == 422


def test_create_application_invalid_source(client):
    resp = client.post("/api/v1/applications", json={"company": "A", "position": "B", "source": "twitter"})
    assert resp.status_code == 422


def test_create_application_invalid_work_arrangement(client):
    resp = client.post("/api/v1/applications", json={"company": "A", "position": "B", "work_arrangement": "moon"})
    assert resp.status_code == 422
