import pytest
from sqlalchemy.exc import IntegrityError

from backend.models.experience import Experience, ExperienceBullet


def test_experience_created_with_defaults(test_session):
    exp = Experience(
        title="Senior Associate",
        company="Secretariat Advisors",
        employment_type="full_time",
        start_date="2022-09",
        source="manual",
    )
    test_session.add(exp)
    test_session.flush()

    assert exp.id is not None
    assert len(exp.id) == 32
    assert exp.is_current is False
    assert exp.end_date is None
    assert exp.created_at is not None


def test_experience_id_is_uuid_hex(test_session):
    exp = Experience(
        title="Intern",
        company="Charles Schwab",
        employment_type="internship",
        start_date="2021-06",
        end_date="2021-08",
        source="manual",
    )
    test_session.add(exp)
    test_session.flush()
    assert len(exp.id) == 32
    assert exp.id.isalnum()


def test_experience_bullet_links_to_experience(test_session):
    exp = Experience(
        title="Analyst",
        company="TestCo",
        employment_type="full_time",
        start_date="2023-01",
        source="manual",
    )
    test_session.add(exp)
    test_session.flush()

    bullet = ExperienceBullet(
        experience_id=exp.id,
        bullet_text="Built a Python pipeline for data processing.",
        confidence_level="verified",
    )
    test_session.add(bullet)
    test_session.flush()

    assert bullet.experience_id == exp.id
    assert bullet.confidence_level == "verified"


def test_experience_bullet_cascade_delete(test_session):
    exp = Experience(
        title="Analyst",
        company="TestCo",
        employment_type="full_time",
        start_date="2023-01",
        source="manual",
    )
    bullet = ExperienceBullet(
        bullet_text="Bullet text",
        confidence_level="verified",
    )
    exp.bullets.append(bullet)
    test_session.add(exp)
    test_session.flush()

    bullet_id = bullet.id
    test_session.delete(exp)
    test_session.flush()

    deleted = test_session.get(ExperienceBullet, bullet_id)
    assert deleted is None
