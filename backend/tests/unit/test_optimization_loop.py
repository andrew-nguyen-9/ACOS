from backend.services.optimization.loop import LearningLoop
from backend.repositories.outcome import OutcomeSignalRepository
from backend.repositories.system_config import SystemConfigRepository
from backend.services.learning.ranker import _SIGNAL_WEIGHTS
from backend.models.application import Application


def _seed_apps(session, n, signal="interview", template="A", industry="ai"):
    repo = OutcomeSignalRepository(session)
    for _ in range(n):
        app = Application(company="C", position="P"); session.add(app); session.flush()
        repo.create(application_id=app.id, signal_type=signal,
                    signal_weight=_SIGNAL_WEIGHTS[signal], ats_score=70,
                    template_used=template, industry=industry)
    session.commit()


def test_should_run_on_multiple_of_trigger(test_session):
    cfg = SystemConfigRepository(test_session)
    cfg.set_value("learning_trigger_count", "5"); test_session.commit()
    loop = LearningLoop(test_session)
    _seed_apps(test_session, 4)
    assert loop.should_run() is False
    _seed_apps(test_session, 1)            # now 5
    assert loop.should_run() is True


def test_maybe_run_creates_proposals_when_triggered(test_session):
    cfg = SystemConfigRepository(test_session)
    cfg.set_value("learning_trigger_count", "5"); test_session.commit()
    # 5 of template A (100% interview) + 5 of template B (0%) → template proposal expected
    _seed_apps(test_session, 5, signal="interview", template="A")
    _seed_apps(test_session, 5, signal="no_response", template="B")
    loop = LearningLoop(test_session)
    out = loop.maybe_run(); test_session.commit()
    assert out["ran"] is True
    assert out["proposals_created"] >= 1
    assert "interview_rate" in out["metrics"]


def test_maybe_run_skips_when_not_triggered(test_session):
    cfg = SystemConfigRepository(test_session)
    cfg.set_value("learning_trigger_count", "5"); test_session.commit()
    _seed_apps(test_session, 3)
    loop = LearningLoop(test_session)
    out = loop.maybe_run()
    assert out["ran"] is False
