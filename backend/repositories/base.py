from typing import Generic, TypeVar, Type

from sqlalchemy import select, func
from sqlalchemy.orm import Session

from backend.models.base import Base

T = TypeVar("T", bound=Base)


class BaseRepository(Generic[T]):
    def __init__(self, model: Type[T], session: Session) -> None:
        self.model = model
        self.session = session

    def get(self, id: str) -> T | None:
        return self.session.get(self.model, id)

    def list(self) -> list[T]:
        return list(self.session.scalars(select(self.model)).all())

    def create(self, **kwargs: object) -> T:
        obj = self.model(**kwargs)
        self.session.add(obj)
        self.session.flush()
        self.session.refresh(obj)
        return obj

    def delete(self, id: str) -> bool:
        obj = self.get(id)
        if obj is None:
            return False
        self.session.delete(obj)
        self.session.flush()
        return True

    def count(self) -> int:
        result = self.session.execute(select(func.count()).select_from(self.model))
        return result.scalar_one()
