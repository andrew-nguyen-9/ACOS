from backend.services.optimization.prompt_evolver import PromptEvolver
from backend.repositories.optimization import PromptVersionRepository


def test_seed_from_disk_creates_active_version(test_session):
    ev = PromptEvolver(test_session)
    v = ev.seed_from_disk("resume/generate")   # real on-disk prompt
    test_session.commit()
    assert v.is_active is True
    assert v.content_yaml                       # non-empty
    # idempotent
    again = ev.seed_from_disk("resume/generate")
    assert again.id == v.id


def test_create_variant_increments_minor(test_session):
    ev = PromptEvolver(test_session)
    base = ev.seed_from_disk("resume/score_ats"); test_session.commit()
    variant = ev.create_variant(
        "resume/score_ats", content_yaml="system: tuned", change_rationale="tighter scoring"
    )
    test_session.commit()
    assert variant.is_active is False
    assert variant.parent_version == base.version
    # version string advanced
    assert variant.version != base.version


def test_activate_and_revert(test_session):
    ev = PromptEvolver(test_session)
    base = ev.seed_from_disk("resume/generate"); test_session.commit()
    variant = ev.create_variant("resume/generate", "system: v2", "experiment")
    test_session.commit()
    ev.activate(variant.id); test_session.commit()
    assert ev.get_active_content("resume/generate") == "system: v2"
    # revert by re-activating base
    ev.activate(base.id); test_session.commit()
    assert ev.get_active_content("resume/generate") == base.content_yaml
