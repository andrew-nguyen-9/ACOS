import pytest
from backend.repositories.optimization import PromptVersionRepository


def test_activate_enforces_single_active(test_session):
    repo = PromptVersionRepository(test_session)
    v1 = repo.create(prompt_name="resume/generate", version="1.0",
                     content_yaml="system: a", is_active=True)
    v2 = repo.create(prompt_name="resume/generate", version="1.1",
                     content_yaml="system: b", parent_version="1.0",
                     change_rationale="tighter bullet rules")
    test_session.commit()

    repo.activate(v2.id)
    test_session.commit()

    active = repo.get_active("resume/generate")
    assert active is not None and active.version == "1.1"
    # v1 was deactivated, not deleted (reversibility)
    assert repo.get(v1.id).is_active is False
    assert len(repo.list_for_prompt("resume/generate")) == 2


def test_revert_by_reactivating_prior(test_session):
    repo = PromptVersionRepository(test_session)
    v1 = repo.create(prompt_name="ats/score_ats", version="1.0",
                     content_yaml="system: a", is_active=True)
    v2 = repo.create(prompt_name="ats/score_ats", version="1.1",
                     content_yaml="system: b")
    test_session.commit()
    repo.activate(v2.id); test_session.commit()
    repo.activate(v1.id); test_session.commit()   # revert
    assert repo.get_active("ats/score_ats").version == "1.0"


def test_duplicate_version_rejected(test_session):
    repo = PromptVersionRepository(test_session)
    repo.create(prompt_name="ats/score_ats", version="1.0", content_yaml="a")
    with pytest.raises(Exception):  # IntegrityError, unique (prompt_name, version)
        repo.create(prompt_name="ats/score_ats", version="1.0", content_yaml="b")
        test_session.commit()
