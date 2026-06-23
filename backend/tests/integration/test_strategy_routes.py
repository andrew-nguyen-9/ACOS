"""Integration tests for Phase 9 Strategy API routes."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from backend.main import create_app

_JD = (
    "We are looking for a Senior Data Analyst with strong Python and SQL skills. "
    "You will build ETL pipelines, maintain Tableau dashboards, and work cross-functionally "
    "with engineering and product teams. Experience with dbt and Airflow preferred. "
    "You will define KPIs and present insights to executive stakeholders."
)

_MOCK_FIT = {
    "overall": 72.5,
    "skill_overlap": 65.0,
    "experience_alignment": 75.0,
    "industry_alignment": 80.0,
    "historical_similarity": 55.0,
    "explanation": "Moderate fit.",
    "risk_factors": [],
    "missing_critical_skills": ["dbt"],
    "confidence": "weak_inference",
}

_MOCK_PATH = {
    "category": "data_analytics",
    "interview_probability": 0.45,
    "offer_probability": 0.1,
    "expected_timeline_days": None,
    "difficulty_rating": 0.55,
    "sample_size": 2,
    "confidence": "weak_inference",
}


@pytest.fixture
def client():
    app = create_app()
    with TestClient(app) as c:
        yield c


# ── POST /strategy/role-fit ───────────────────────────────────────────────────

class TestRoleFitRoute:
    def test_returns_200(self, client):
        with patch("backend.api.v1.routes.strategy.RoleFitScorer") as MockScorer:
            MockScorer.return_value.score.return_value = _MOCK_FIT
            resp = client.post("/api/v1/strategy/role-fit", json={"jd_text": _JD})
        assert resp.status_code == 200

    def test_response_shape(self, client):
        with patch("backend.api.v1.routes.strategy.RoleFitScorer") as MockScorer:
            MockScorer.return_value.score.return_value = _MOCK_FIT
            resp = client.post("/api/v1/strategy/role-fit", json={"jd_text": _JD})
        data = resp.json()
        assert "overall" in data
        assert "confidence" in data
        assert 0 <= data["overall"] <= 100

    def test_short_jd_422(self, client):
        resp = client.post("/api/v1/strategy/role-fit", json={"jd_text": "short"})
        assert resp.status_code == 422


# ── GET /strategy/career-paths ────────────────────────────────────────────────

class TestCareerPathsRoute:
    def test_returns_list(self, client):
        with patch("backend.api.v1.routes.strategy.CareerPathSimulator") as MockSim:
            MockSim.return_value.simulate_all.return_value = [_MOCK_PATH]
            resp = client.get("/api/v1/strategy/career-paths")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_result_has_required_keys(self, client):
        with patch("backend.api.v1.routes.strategy.CareerPathSimulator") as MockSim:
            MockSim.return_value.simulate_all.return_value = [_MOCK_PATH]
            resp = client.get("/api/v1/strategy/career-paths")
        if resp.json():
            for key in ("category", "interview_probability", "offer_probability", "confidence"):
                assert key in resp.json()[0]


# ── POST /strategy/prioritize ─────────────────────────────────────────────────

class TestPrioritizeRoute:
    def test_returns_list(self, client):
        with patch("backend.api.v1.routes.strategy.ApplicationStrategyEngine") as MockEng:
            MockEng.return_value.prioritize.return_value = [
                {
                    "job_id": "j1", "jd_snippet": "...", "priority": "tailor",
                    "reason": "ok", "fit_score": 65.0, "confidence": "strong_inference",
                    "missing_critical_skills": [], "risk_factors": [],
                    "explanation": "Moderate fit.", "top_pick": False,
                }
            ]
            resp = client.post(
                "/api/v1/strategy/prioritize",
                json={"jobs": [{"job_id": "j1", "jd_text": _JD}]},
            )
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_empty_jobs_ok(self, client):
        with patch("backend.api.v1.routes.strategy.ApplicationStrategyEngine") as MockEng:
            MockEng.return_value.prioritize.return_value = []
            resp = client.post("/api/v1/strategy/prioritize", json={"jobs": []})
        assert resp.status_code == 200

    def test_response_carries_confidence_and_evidence(self, client):
        # ADR-012: no bare numbers — each ranked row carries confidence + evidence.
        with patch("backend.api.v1.routes.strategy.ApplicationStrategyEngine") as MockEng:
            MockEng.return_value.prioritize.return_value = [
                {
                    "job_id": "j1",
                    "jd_snippet": "...",
                    "priority": "tailor",
                    "reason": "ok",
                    "fit_score": 65.0,
                    "confidence": "strong_inference",
                    "missing_critical_skills": ["dbt"],
                    "risk_factors": [],
                    "explanation": "Moderate fit.",
                    "top_pick": True,
                }
            ]
            resp = client.post(
                "/api/v1/strategy/prioritize",
                json={"jobs": [{"job_id": "j1", "jd_text": _JD}]},
            )
        assert resp.status_code == 200
        row = resp.json()[0]
        for key in ("confidence", "missing_critical_skills", "explanation", "top_pick"):
            assert key in row


# ── GET /strategy/skill-gaps ──────────────────────────────────────────────────

class TestSkillGapsRoute:
    def test_returns_list(self, client):
        with patch("backend.api.v1.routes.strategy.SkillGapForecaster") as MockFG:
            MockFG.return_value.forecast.return_value = []
            resp = client.get("/api/v1/strategy/skill-gaps")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)


# ── GET /strategy/resume-recommendation ──────────────────────────────────────

class TestResumeRecommendationRoute:
    def test_returns_recommendation(self, client):
        with patch("backend.api.v1.routes.strategy.ResumeStrategySelector") as MockSel:
            MockSel.return_value.recommend.return_value = {
                "template_name": "data_technical",
                "bullet_emphasis": ["technical", "quantification", "impact"],
                "keyword_priorities": ["python", "sql"],
                "reason": "Data role detected.",
                "requires_approval": True,
            }
            resp = client.get("/api/v1/strategy/resume-recommendation", params={"jd_text": _JD})
        assert resp.status_code == 200
        assert resp.json()["requires_approval"] is True

    def test_short_jd_422(self, client):
        resp = client.get("/api/v1/strategy/resume-recommendation", params={"jd_text": "too short"})
        assert resp.status_code == 422


# ── GET /analytics/outcomes ───────────────────────────────────────────────────

class TestOutcomesRoute:
    def test_returns_report(self, client):
        with patch("backend.api.v1.routes.strategy.OutcomeLearner") as MockOL:
            MockOL.return_value.outcome_report.return_value = {
                "category_breakdown": [],
                "ats_threshold": [
                    {"range": r, "outcome_rate": 0.0, "count": 0}
                    for r in ["0-20", "20-40", "40-60", "60-80", "80-100"]
                ],
                "total_signals": 0,
            }
            resp = client.get("/api/v1/analytics/outcomes")
        assert resp.status_code == 200
        data = resp.json()
        assert "total_signals" in data
        assert len(data["ats_threshold"]) == 5
