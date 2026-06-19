from __future__ import annotations

import pytest

from backend.models.application import Application
from backend.models.resume import Resume, ResumeTemplate, WritingProfile
from backend.repositories.resume import (
    ResumeRepository,
    ResumeTemplateRepository,
    WritingProfileRepository,
)


@pytest.fixture
def resume_repo(test_session):
    return ResumeRepository(test_session)


@pytest.fixture
def template_repo(test_session):
    return ResumeTemplateRepository(test_session)


@pytest.fixture
def profile_repo(test_session):
    return WritingProfileRepository(test_session)


# --- ResumeRepository ---

def test_get_by_application_returns_matching(test_session, resume_repo):
    # Create an Application record first to satisfy FK constraint
    app = Application(company="Acme", position="Engineer", status="draft")
    test_session.add(app)
    test_session.flush()
    r = Resume(name="My Resume", application_id=app.id, content_json={})
    test_session.add(r)
    test_session.flush()
    results = resume_repo.get_by_application(app.id)
    assert len(results) == 1
    assert results[0].application_id == app.id


def test_get_by_application_returns_empty_for_unknown(resume_repo):
    results = resume_repo.get_by_application("nonexistent")
    assert results == []


def test_get_master_returns_master_resume(test_session, resume_repo):
    r = Resume(name="Master", is_master=True, content_json={})
    test_session.add(r)
    test_session.flush()
    master = resume_repo.get_master()
    assert master is not None
    assert master.is_master is True


def test_get_master_returns_none_when_absent(resume_repo):
    result = resume_repo.get_master()
    assert result is None


# --- ResumeTemplateRepository ---

def test_get_default_template(test_session, template_repo):
    t = ResumeTemplate(name="Default", layout_type="single_column", is_default=True, template_json={})
    test_session.add(t)
    test_session.flush()
    result = template_repo.get_default()
    assert result is not None
    assert result.is_default is True


def test_get_default_returns_none_when_absent(template_repo):
    result = template_repo.get_default()
    assert result is None


def test_get_by_industry(test_session, template_repo):
    t = ResumeTemplate(
        name="Tech Template",
        layout_type="single_column",
        target_industry="software",
        template_json={},
    )
    test_session.add(t)
    test_session.flush()
    result = template_repo.get_by_industry("software")
    assert result is not None
    assert result.target_industry == "software"


def test_get_by_industry_returns_none_for_unknown(template_repo):
    result = template_repo.get_by_industry("nonexistent_industry")
    assert result is None


# --- WritingProfileRepository ---

def test_get_latest_returns_most_recent(test_session, profile_repo):
    p1 = WritingProfile(
        tone_descriptors=["professional"],
        structure_patterns=[],
        vocabulary_patterns={},
        sample_sentences=[],
        source_doc_ids=[],
    )
    test_session.add(p1)
    test_session.flush()
    result = profile_repo.get_latest()
    assert result is not None
    assert result.tone_descriptors == ["professional"]


def test_get_latest_returns_none_when_empty(profile_repo):
    result = profile_repo.get_latest()
    assert result is None
