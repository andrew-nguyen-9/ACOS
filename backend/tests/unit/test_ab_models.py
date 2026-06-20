from backend.repositories.optimization import (
    ABExperimentRepository, ABVariantRepository,
)


def test_experiment_with_variants(test_session):
    exp_repo = ABExperimentRepository(test_session)
    var_repo = ABVariantRepository(test_session)
    exp = exp_repo.create(name="Resume A vs B", target_engine="resume")
    test_session.commit()
    assert exp.metric == "interview_conversion_rate"   # default
    assert exp.status == "running"

    a = var_repo.create(experiment_id=exp.id, label="A", config_json='{"template":"software"}')
    b = var_repo.create(experiment_id=exp.id, label="B", config_json='{"template":"modern"}')
    test_session.commit()
    assert a.impressions == 0 and a.conversions == 0
    variants = var_repo.list_for_experiment(exp.id)
    assert {v.label for v in variants} == {"A", "B"}


def test_list_running(test_session):
    exp_repo = ABExperimentRepository(test_session)
    exp_repo.create(name="r1", target_engine="ats")
    concluded = exp_repo.create(name="r2", target_engine="rag", status="concluded")
    test_session.commit()
    running = exp_repo.list_running()
    assert len(running) == 1
    assert running[0].name == "r1"
