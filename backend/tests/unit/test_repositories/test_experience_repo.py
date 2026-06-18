import pytest
from backend.repositories.experience import ExperienceRepository
from backend.models.experience import Experience, ExperienceBullet


@pytest.fixture
def repo(test_session):
    return ExperienceRepository(test_session)


def _make_exp(company="Secretariat", title="Senior Associate", source="manual") -> Experience:
    return Experience(
        title=title,
        company=company,
        employment_type="full_time",
        start_date="2022-09",
        source=source,
    )


def test_create_and_get(repo, test_session):
    exp = repo.create(
        title="Analyst",
        company="TestCo",
        employment_type="full_time",
        start_date="2023-01",
        source="manual",
    )
    assert exp.id is not None
    fetched = repo.get(exp.id)
    assert fetched is not None
    assert fetched.company == "TestCo"


def test_list_returns_all(repo):
    repo.create(title="A", company="Co1", employment_type="full_time", start_date="2022-01", source="manual")
    repo.create(title="B", company="Co2", employment_type="full_time", start_date="2023-01", source="manual")
    assert len(repo.list()) == 2


def test_delete_returns_true(repo):
    exp = repo.create(title="X", company="Y", employment_type="full_time", start_date="2021-01", source="manual")
    assert repo.delete(exp.id) is True
    assert repo.get(exp.id) is None


def test_delete_nonexistent_returns_false(repo):
    assert repo.delete("doesnotexist") is False


def test_get_by_company(repo):
    repo.create(title="A", company="Secretariat", employment_type="full_time", start_date="2022-01", source="manual")
    repo.create(title="B", company="Schwab", employment_type="internship", start_date="2021-06", source="manual")
    results = repo.get_by_company("Secretariat")
    assert len(results) == 1
    assert results[0].company == "Secretariat"


def test_get_current_returns_only_current_jobs(repo):
    repo.create(title="Old", company="A", employment_type="full_time", start_date="2020-01", source="manual", is_current=False)
    repo.create(title="Current", company="B", employment_type="full_time", start_date="2022-09", source="manual", is_current=True)
    current = repo.get_current()
    assert len(current) == 1
    assert current[0].title == "Current"


def test_add_bullet(repo, test_session):
    exp = repo.create(title="X", company="Y", employment_type="full_time", start_date="2023-01", source="manual")
    bullet = repo.add_bullet(
        experience_id=exp.id,
        bullet_text="Built a Python pipeline.",
        confidence_level="verified",
    )
    assert bullet.id is not None
    assert bullet.experience_id == exp.id
