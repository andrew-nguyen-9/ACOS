"""Unit tests for Phase 9 strategy services."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from backend.services.strategy.application_strategy import ApplicationStrategyEngine
from backend.services.strategy.career_path_simulator import CareerPathSimulator, _match_category
from backend.services.strategy.outcome_learner import OutcomeLearner
from backend.services.strategy.resume_strategy_selector import (
    ResumeStrategySelector,
    _detect_category,
    _extract_top_keywords,
)
from backend.services.strategy.role_fit_scorer import RoleFitScorer, _jd_hash, _tokenize
from backend.services.strategy.skill_gap_forecaster import SkillGapForecaster


# ── helpers ──────────────────────────────────────────────────────────────────

def _mock_signal(signal_type: str, weight: float, position_type: str = "data analyst", industry: str = "tech", ats_score: float | None = None):
    s = MagicMock()
    s.signal_type = signal_type
    s.signal_weight = weight
    s.position_type = position_type
    s.industry = industry
    s.ats_score = ats_score
    s.template_used = None
    return s


def _mock_skill(name: str, proficiency: str = "intermediate"):
    s = MagicMock()
    s.name = name
    s.proficiency = proficiency
    return s


def _session_with(signals=None, skills=None):
    session = MagicMock()
    return session


# ── _tokenize / _jd_hash ─────────────────────────────────────────────────────

def test_tokenize_basic():
    tokens = _tokenize("Python SQL machine learning")
    assert "python" in tokens
    assert "sql" in tokens


def test_jd_hash_deterministic():
    assert _jd_hash("hello world") == _jd_hash("hello world")
    assert _jd_hash("hello world") != _jd_hash("goodbye world")


def test_jd_hash_length():
    assert len(_jd_hash("x")) == 32


# ── _match_category ───────────────────────────────────────────────────────────

def test_match_category_product():
    assert _match_category("Senior Product Manager, OKR roadmap") == "product_management"


def test_match_category_data():
    assert _match_category("Data Analyst, SQL ETL pipeline") == "data_analytics"


def test_match_category_none():
    assert _match_category(None) is None


def test_match_category_empty():
    assert _match_category("") is None


# ── _detect_category ─────────────────────────────────────────────────────────

def test_detect_category_consulting():
    jd = "Strategy consulting engagement workstream client advisory management consulting"
    assert _detect_category(jd) == "consulting"


def test_detect_category_default():
    assert _detect_category("random words here") == "product_management"


# ── _extract_top_keywords ────────────────────────────────────────────────────

def test_extract_top_keywords_count():
    jd = "python python sql sql aws docker python"
    kws = _extract_top_keywords(jd, top_n=3)
    assert len(kws) <= 3
    assert kws[0] == "python"


def test_extract_top_keywords_excludes_stopwords():
    jd = "you will work and the team are ready"
    kws = _extract_top_keywords(jd, top_n=10)
    stop = {"you", "will", "and", "the", "are"}
    assert not (set(kws) & stop)


# ── RoleFitScorer ─────────────────────────────────────────────────────────────

class TestRoleFitScorer:
    def _make_scorer(self, skills=None, signals=None):
        session = MagicMock()
        scorer = RoleFitScorer(session)

        with patch("backend.services.strategy.role_fit_scorer.SkillRepository") as MockSR, \
             patch("backend.services.strategy.role_fit_scorer.OutcomeSignalRepository") as MockOR:
            MockSR.return_value.list.return_value = skills or []
            MockOR.return_value.list.return_value = signals or []
            result = scorer.score("Python SQL machine learning data analytics pipeline ETL")
        return result

    def test_returns_required_keys(self):
        result = self._make_scorer()
        for key in ("overall", "skill_overlap", "experience_alignment", "industry_alignment",
                    "historical_similarity", "explanation", "risk_factors", "missing_critical_skills", "confidence"):
            assert key in result

    def test_overall_range(self):
        result = self._make_scorer()
        assert 0 <= result["overall"] <= 100

    def test_confidence_weak_with_no_signals(self):
        result = self._make_scorer(signals=[])
        assert result["confidence"] == "weak_inference"

    def test_confidence_verified_with_many_signals(self):
        signals = [_mock_signal("interview", 0.7) for _ in range(10)]
        with patch("backend.services.strategy.role_fit_scorer.SkillRepository") as MockSR, \
             patch("backend.services.strategy.role_fit_scorer.OutcomeSignalRepository") as MockOR:
            session = MagicMock()
            scorer = RoleFitScorer(session)
            MockSR.return_value.list.return_value = []
            MockOR.return_value.list.return_value = signals
            result = scorer.score("Python SQL analytics pipeline data science")
        assert result["confidence"] == "verified"

    def test_missing_critical_skills_subset(self):
        result = self._make_scorer(skills=[_mock_skill("python")])
        # python is in user skills; other critical skills may be in missing list
        assert isinstance(result["missing_critical_skills"], list)


# ── CareerPathSimulator ───────────────────────────────────────────────────────

class TestCareerPathSimulator:
    def _simulate(self, signals):
        session = MagicMock()
        sim = CareerPathSimulator(session)
        with patch("backend.services.strategy.career_path_simulator.OutcomeSignalRepository") as MockOR:
            MockOR.return_value.list.return_value = signals
            return sim.simulate_all()

    def test_returns_all_categories(self):
        results = self._simulate([])
        cats = {r["category"] for r in results}
        from backend.services.strategy.career_path_simulator import CATEGORY_KEYWORDS
        assert cats == set(CATEGORY_KEYWORDS.keys())

    def test_zero_signals_weak_confidence(self):
        results = self._simulate([])
        for r in results:
            assert r["confidence"] == "weak_inference"
            assert r["sample_size"] == 0

    def test_interview_probability_calculation(self):
        signals = [
            _mock_signal("interview", 0.7, "Data Analyst SQL ETL pipeline"),
            _mock_signal("no_response", 0.0, "Data Analyst SQL ETL pipeline"),
        ]
        results = self._simulate(signals)
        data_cat = next(r for r in results if r["category"] == "data_analytics")
        assert data_cat["interview_probability"] == 0.5

    def test_difficulty_complementary(self):
        signals = [_mock_signal("interview", 0.7, "Data Analyst SQL pipeline")]
        results = self._simulate(signals)
        data_cat = next(r for r in results if r["category"] == "data_analytics")
        assert abs(data_cat["difficulty_rating"] - (1.0 - data_cat["interview_probability"])) < 0.01


# ── ApplicationStrategyEngine ─────────────────────────────────────────────────

class TestApplicationStrategyEngine:
    def _prioritize(self, jobs, overall=80.0, missing=0):
        session = MagicMock()
        engine = ApplicationStrategyEngine(session)
        with patch.object(engine._scorer, "score", return_value={
            "overall": overall,
            "missing_critical_skills": ["python"] * missing,
            "risk_factors": [],
        }), \
        patch("backend.repositories.skill.SkillRepository") as MockSR:
            MockSR.return_value.list.return_value = []
            return engine.prioritize(jobs)

    def test_prioritize_high_score(self):
        results = self._prioritize([{"job_id": "j1", "jd_text": "Python SQL analytics " * 5}], overall=80.0, missing=0)
        assert results[0]["priority"] == "prioritize"

    def test_tailor_mid_score(self):
        results = self._prioritize([{"job_id": "j2", "jd_text": "strategy consulting " * 5}], overall=60.0, missing=0)
        assert results[0]["priority"] == "tailor"

    def test_skip_low_score(self):
        results = self._prioritize([{"job_id": "j3", "jd_text": "random job " * 5}], overall=25.0, missing=5)
        assert results[0]["priority"] == "skip"

    def test_empty_jobs(self):
        results = self._prioritize([])
        assert results == []

    def test_skips_empty_jd_text(self):
        session = MagicMock()
        engine = ApplicationStrategyEngine(session)
        with patch.object(engine._scorer, "score", return_value={"overall": 80, "missing_critical_skills": [], "risk_factors": []}):
            results = engine.prioritize([{"job_id": "j1", "jd_text": ""}])
        assert results == []


# ── SkillGapForecaster ────────────────────────────────────────────────────────

class TestSkillGapForecaster:
    def _forecast(self, signals=None, skills=None):
        session = MagicMock()
        forecaster = SkillGapForecaster(session)
        with patch("backend.services.strategy.skill_gap_forecaster.OutcomeSignalRepository") as MockOR, \
             patch("backend.services.strategy.skill_gap_forecaster.SkillRepository") as MockSR:
            MockOR.return_value.list.return_value = signals or []
            MockSR.return_value.list.return_value = skills or []
            return forecaster.forecast()

    def test_no_signals_empty_result(self):
        assert self._forecast() == []

    def test_missing_skill_identified(self):
        signals = [
            _mock_signal("no_response", 0.0, "python sql analytics pipeline etl", ats_score=45),
        ]
        results = self._forecast(signals=signals)
        skill_names = {r["skill_name"] for r in results}
        assert "sql" in skill_names or "python" in skill_names

    def test_proficient_skill_excluded(self):
        signals = [_mock_signal("no_response", 0.0, "python sql analytics")]
        skills = [_mock_skill("python", "advanced"), _mock_skill("sql", "expert")]
        results = self._forecast(signals=signals, skills=skills)
        skill_names = {r["skill_name"] for r in results}
        assert "python" not in skill_names
        assert "sql" not in skill_names

    def test_sorted_by_priority_rank(self):
        signals = [_mock_signal("no_response", 0.0, "python sql airflow dbt") for _ in range(3)]
        results = self._forecast(signals=signals)
        if len(results) >= 2:
            assert results[0]["priority_rank"] >= results[1]["priority_rank"]


# ── ResumeStrategySelector ────────────────────────────────────────────────────

class TestResumeStrategySelector:
    def _recommend(self, jd_text):
        session = MagicMock()
        selector = ResumeStrategySelector(session)
        return selector.recommend(jd_text)

    def test_requires_approval_always_true(self):
        result = self._recommend("product manager roadmap OKR user research sprint stakeholder")
        assert result["requires_approval"] is True

    def test_pm_category_emphasis(self):
        result = self._recommend("product manager roadmap OKR user research sprint stakeholder")
        assert "leadership" in result["bullet_emphasis"] or "impact" in result["bullet_emphasis"]

    def test_data_category_emphasis(self):
        result = self._recommend("data analyst SQL ETL pipeline tableau dashboard analytics")
        assert "technical" in result["bullet_emphasis"]

    def test_returns_keyword_priorities(self):
        result = self._recommend("python sql machine learning data pipeline analytics model")
        assert len(result["keyword_priorities"]) > 0

    def test_returns_template_name(self):
        result = self._recommend("consulting strategy engagement client advisory workstream")
        assert result["template_name"] in ("pm_executive", "data_technical", "consulting_narrative")


# ── OutcomeLearner ────────────────────────────────────────────────────────────

class TestOutcomeLearner:
    def _report(self, signals=None):
        session = MagicMock()
        learner = OutcomeLearner(session)
        with patch("backend.services.strategy.outcome_learner.OutcomeSignalRepository") as MockOR:
            MockOR.return_value.list.return_value = signals or []
            return learner.outcome_report()

    def test_empty_signals(self):
        report = self._report([])
        assert report["total_signals"] == 0
        assert report["category_breakdown"] == []
        assert len(report["ats_threshold"]) == 5

    def test_ats_buckets_count(self):
        report = self._report()
        assert len(report["ats_threshold"]) == 5

    def test_total_signals_count(self):
        signals = [_mock_signal("interview", 0.7) for _ in range(4)]
        report = self._report(signals)
        assert report["total_signals"] == 4

    def test_category_breakdown_structure(self):
        signals = [
            _mock_signal("interview", 0.7, "data analyst sql pipeline"),
            _mock_signal("no_response", 0.0, "data analyst sql pipeline"),
        ]
        report = self._report(signals)
        if report["category_breakdown"]:
            entry = report["category_breakdown"][0]
            for key in ("category", "total", "interview_rate", "offer_rate", "avg_signal_weight", "confidence"):
                assert key in entry

    def test_ats_bucket_labels(self):
        report = self._report()
        labels = {b["range"] for b in report["ats_threshold"]}
        assert labels == {"0-20", "20-40", "40-60", "60-80", "80-100"}
