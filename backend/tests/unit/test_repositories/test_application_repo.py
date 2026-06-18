import pytest
from backend.repositories.application import ApplicationRepository
from backend.models.application import Application, ApplicationTimeline


@pytest.fixture
def repo(test_session):
    return ApplicationRepository(test_session)


def test_create_application(repo):
    app = repo.create(company="Acme", position="PM")
    assert app.id is not None
    assert app.status == "draft"


def test_get_by_status(repo):
    repo.create(company="A", position="PM", status="applied")
    repo.create(company="B", position="SWE", status="draft")
    applied = repo.get_by_status("applied")
    assert len(applied) == 1
    assert applied[0].company == "A"


def test_get_by_company(repo):
    repo.create(company="Google", position="APM")
    repo.create(company="Meta", position="TPM")
    results = repo.get_by_company("Google")
    assert len(results) == 1
    assert results[0].company == "Google"


def test_record_timeline_event(repo, test_session):
    app = repo.create(company="Google", position="APM")
    event = repo.record_timeline_event(
        application_id=app.id,
        event_type="status_change",
        from_status="draft",
        to_status="applied",
        note="Submitted application",
    )
    assert event.id is not None
    assert event.application_id == app.id
    assert event.from_status == "draft"
    assert event.to_status == "applied"


def test_transition_status_updates_and_logs(repo, test_session):
    app = repo.create(company="Apple", position="PM", status="applied")
    updated = repo.transition_status(app.id, "phone_screen")
    assert updated is not None
    assert updated.status == "phone_screen"

    test_session.refresh(updated)
    events = [e for e in updated.timeline if e.event_type == "status_change"]
    assert len(events) == 1
    assert events[0].from_status == "applied"
    assert events[0].to_status == "phone_screen"


def test_transition_status_nonexistent_returns_none(repo):
    result = repo.transition_status("doesnotexist", "applied")
    assert result is None


def test_delete_application(repo):
    app = repo.create(company="Netflix", position="DS")
    assert repo.delete(app.id) is True
    assert repo.get(app.id) is None
