from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models.question import Answer, Question
from backend.repositories.base import BaseRepository


class QuestionRepository(BaseRepository[Question]):
    def __init__(self, session: Session) -> None:
        super().__init__(Question, session)

    def get_by_category(self, category: str) -> list[Question]:
        return list(
            self.session.scalars(
                select(Question).where(Question.category == category)
            ).all()
        )

    def get_by_source(self, source: str) -> list[Question]:
        return list(
            self.session.scalars(
                select(Question).where(Question.source == source)
            ).all()
        )


class AnswerRepository(BaseRepository[Answer]):
    def __init__(self, session: Session) -> None:
        super().__init__(Answer, session)

    def get_by_question(self, question_id: str) -> list[Answer]:
        return list(
            self.session.scalars(
                select(Answer).where(Answer.question_id == question_id)
            ).all()
        )

    def get_by_application(self, application_id: str) -> list[Answer]:
        return list(
            self.session.scalars(
                select(Answer).where(Answer.application_id == application_id)
            ).all()
        )

    def get_latest(self, question_id: str) -> Answer | None:
        results = list(
            self.session.scalars(
                select(Answer)
                .where(Answer.question_id == question_id)
                .order_by(Answer.created_at.desc())
                .limit(1)
            ).all()
        )
        return results[0] if results else None
