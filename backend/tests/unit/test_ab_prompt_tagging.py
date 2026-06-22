"""TDD for A/B runs tagged with prompt name+version + comparison (Phase 11.2)."""
from backend.services.optimization.ab_testing import ABTestingService


def test_create_prompt_experiment_tags_versions(test_session):
    svc = ABTestingService(test_session)
    exp = svc.create_prompt_experiment(
        name="resume tone test",
        target_engine="resume",
        prompt_name="resume_generate",
        version_a="v1",
        version_b="v2",
    )
    report = svc.comparison(exp.id)
    by_label = {v["label"]: v for v in report["variants"]}
    assert by_label["A"]["prompt_name"] == "resume_generate"
    assert by_label["A"]["version"] == "v1"
    assert by_label["B"]["version"] == "v2"


def test_comparison_includes_conversion_rates(test_session):
    svc = ABTestingService(test_session)
    exp = svc.create_prompt_experiment(
        name="t", target_engine="resume",
        prompt_name="resume_generate", version_a="v1", version_b="v2",
    )
    variants = {v["label"]: v["id"] for v in svc.comparison(exp.id)["variants"]}
    svc.record_impression(variants["A"])
    svc.record_impression(variants["A"])
    svc.record_conversion(variants["A"])

    report = svc.comparison(exp.id)
    by_label = {v["label"]: v for v in report["variants"]}
    assert by_label["A"]["impressions"] == 2
    assert by_label["A"]["conversions"] == 1
    assert by_label["A"]["conversion_rate"] == 0.5
    assert report["experiment_id"] == exp.id
