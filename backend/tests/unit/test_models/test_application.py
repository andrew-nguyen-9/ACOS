from backend.models.application import Application, ApplicationTimeline


def test_application_default_status_is_draft(test_session):
    app = Application(company="Acme Corp", position="Product Manager")
    test_session.add(app)
    test_session.flush()

    assert app.status == "draft"
    assert app.currency == "USD"
    assert app.id is not None


def test_application_timeline_links_to_application(test_session):
    app = Application(company="Acme Corp", position="Data Analyst")
    test_session.add(app)
    test_session.flush()

    event = ApplicationTimeline(
        application_id=app.id,
        event_type="status_change",
        from_status="draft",
        to_status="applied",
    )
    test_session.add(event)
    test_session.flush()

    test_session.refresh(app)
    assert len(app.timeline) == 1
    assert app.timeline[0].to_status == "applied"


def test_application_cascade_deletes_timeline(test_session):
    app = Application(company="Acme", position="PM")
    event = ApplicationTimeline(event_type="note_added", note="Follow up")
    app.timeline.append(event)
    test_session.add(app)
    test_session.flush()

    event_id = event.id
    test_session.delete(app)
    test_session.flush()

    assert test_session.get(ApplicationTimeline, event_id) is None
