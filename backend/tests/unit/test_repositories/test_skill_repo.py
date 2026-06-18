import pytest
from backend.repositories.skill import SkillRepository


@pytest.fixture
def repo(test_session):
    return SkillRepository(test_session)


def test_create_skill(repo):
    skill = repo.create(name="Python", category="programming", proficiency="expert")
    assert skill.id is not None
    assert skill.name == "Python"


def test_get_by_name_finds_existing(repo):
    repo.create(name="SQL", category="data")
    found = repo.get_by_name("SQL")
    assert found is not None
    assert found.name == "SQL"


def test_get_by_name_returns_none_for_missing(repo):
    assert repo.get_by_name("Nonexistent") is None


def test_get_by_category(repo):
    repo.create(name="Python", category="programming")
    repo.create(name="SQL", category="data")
    repo.create(name="Tableau", category="tool")
    results = repo.get_by_category("programming")
    assert len(results) == 1
    assert results[0].name == "Python"


def test_get_or_create_creates_new(repo):
    skill, created = repo.get_or_create("GCP", category="tool")
    assert created is True
    assert skill.name == "GCP"


def test_get_or_create_returns_existing(repo):
    repo.create(name="GCP", category="tool")
    skill, created = repo.get_or_create("GCP", category="tool")
    assert created is False


def test_add_evidence(repo, test_session):
    skill = repo.create(name="Python", category="programming")
    ev = repo.add_evidence(
        skill_id=skill.id,
        source_type="experience",
        source_id="exp-123",
        evidence_text="Built ETL pipelines in Python",
        confidence_level="verified",
    )
    assert ev.id is not None
    assert ev.skill_id == skill.id
    assert ev.confidence_level == "verified"
