from typing import Generic, TypeVar, Type, cast

from sqlalchemy import select, func
from sqlalchemy.orm import Session

from backend.models.base import Base
from backend.models.tenant import TenantScopedMixin
from backend.services.tenancy import is_tenant_scoped, require_session_tenant

T = TypeVar("T", bound=Base)


class BaseRepository(Generic[T]):
    """Phase 12.14: the central tenant guard.

    For tenant-scoped models, reads filter to the active tenant and a missing tenant
    is a hard error (``require_session_tenant`` raises). Writes auto-inject the active
    tenant. The ORM ``do_orm_execute`` auto-filter (models/tenant.py) backs custom
    repository methods and relationship loads; these base methods add the hard-error
    on the explicit path. Shared models behave exactly as before.
    """

    def __init__(self, model: Type[T], session: Session) -> None:
        self.model = model
        self.session = session
        self._scoped = is_tenant_scoped(model)
        # Typed handle for the tenant_id column on scoped models (pyright narrowing).
        self._scoped_model = cast("Type[TenantScopedMixin]", model)

    def get(self, id: str) -> T | None:
        obj = self.session.get(self.model, id)
        if obj is None:
            return None
        if self._scoped:
            scoped = cast(TenantScopedMixin, obj)
            if scoped.tenant_id != require_session_tenant(self.session):
                return None  # another tenant's row resolves to None, never the row
        return obj

    def list(self) -> list[T]:
        stmt = select(self.model)
        if self._scoped:
            tenant_id = require_session_tenant(self.session)
            stmt = stmt.where(self._scoped_model.tenant_id == tenant_id)
        return list(self.session.scalars(stmt).all())

    def create(self, **kwargs: object) -> T:
        if self._scoped and "tenant_id" not in kwargs:
            kwargs["tenant_id"] = require_session_tenant(self.session)
        obj = self.model(**kwargs)
        self.session.add(obj)
        self.session.flush()
        self.session.refresh(obj)
        return obj

    def delete(self, id: str) -> bool:
        obj = self.get(id)  # tenant-checked
        if obj is None:
            return False
        self.session.delete(obj)
        self.session.flush()
        return True

    def count(self) -> int:
        stmt = select(func.count()).select_from(self.model)
        if self._scoped:
            tenant_id = require_session_tenant(self.session)
            stmt = stmt.where(self._scoped_model.tenant_id == tenant_id)
        result = self.session.execute(stmt)
        return result.scalar_one()
