from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models.application import Application, ApplicationTimeline
from backend.repositories.base import BaseRepository


class ApplicationRepository(BaseRepository[Application]):
    def __init__(self, session: Session) -> None:
        super().__init__(Application, session)

    def get_by_status(self, status: str) -> list[Application]:
        return list(
            self.session.scalars(
                select(Application).where(Application.status == status)
            ).all()
        )

    def get_by_company(self, company: str) -> list[Application]:
        return list(
            self.session.scalars(
                select(Application).where(Application.company == company)
            ).all()
        )

    def record_timeline_event(
        self,
        application_id: str,
        event_type: str,
        from_status: str | None = None,
        to_status: str | None = None,
        note: str | None = None,
    ) -> ApplicationTimeline:
        event = ApplicationTimeline(
            application_id=application_id,
            event_type=event_type,
            from_status=from_status,
            to_status=to_status,
            note=note,
        )
        self.session.add(event)
        self.session.flush()
        self.session.refresh(event)
        return event

    def transition_status(self, application_id: str, new_status: str) -> Application | None:
        app = self.get(application_id)
        if app is None:
            return None
        old_status = app.status
        app.status = new_status
        self.session.flush()
        self.record_timeline_event(
            application_id=application_id,
            event_type="status_change",
            from_status=old_status,
            to_status=new_status,
        )
        return app
