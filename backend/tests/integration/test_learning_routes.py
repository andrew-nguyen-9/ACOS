from __future__ import annotations


def _make_app(client, company="Acme", position="Engineer"):
    resp = client.post("/api/v1/applications", json={"company": company, "position": position})
    return resp.json()["id"]


def test_record_outcome(client):
    app_id = _make_app(client)
    resp = client.post(
        "/api/v1/learning/outcome",
        json={"application_id": app_id, "signal_type": "interview", "template_used": "software"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["signal_type"] == "interview"
    assert data["signal_weight"] == 0.7
    assert "signal_id" in data


def test_record_outcome_invalid_signal(client):
    app_id = _make_app(client)
    resp = client.post(
        "/api/v1/learning/outcome",
        json={"application_id": app_id, "signal_type": "hired"},
    )
    assert resp.status_code == 422


def test_get_rankings_empty(client):
    resp = client.get("/api/v1/learning/rankings")
    assert resp.status_code == 200
    assert resp.json() == {"template_rankings": []}


def test_get_rankings_with_data(client):
    app_id = _make_app(client)
    client.post(
        "/api/v1/learning/outcome",
        json={"application_id": app_id, "signal_type": "offer", "template_used": "software"},
    )
    resp = client.get("/api/v1/learning/rankings")
    assert resp.status_code == 200
    rankings = resp.json()["template_rankings"]
    assert len(rankings) == 1
    assert rankings[0]["template_name"] == "software"
    assert rankings[0]["score"] == 1.0


def test_get_report(client):
    resp = client.get("/api/v1/learning/report")
    assert resp.status_code == 200
    data = resp.json()
    assert "template_rankings" in data
    assert "ats_vs_outcome" in data
    assert "buckets" in data["ats_vs_outcome"]
    assert "total_signals" in data["ats_vs_outcome"]


def test_get_report_with_ats_data(client):
    app_id = _make_app(client)
    client.post(
        "/api/v1/learning/outcome",
        json={
            "application_id": app_id,
            "signal_type": "offer",
            "ats_score": 90.0,
            "template_used": "software",
        },
    )
    resp = client.get("/api/v1/learning/report")
    assert resp.status_code == 200
    report = resp.json()
    assert report["ats_vs_outcome"]["total_signals"] == 1
    bucket_80 = next(
        b for b in report["ats_vs_outcome"]["buckets"] if b["range"] == "80-100"
    )
    assert bucket_80["count"] == 1
    assert bucket_80["outcome_rate"] == 1.0
