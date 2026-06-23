"""Phase 12.14 tenant isolation — the `tenants` table, the scoping mixin, and the
central auto-filter that makes isolation a property of the ORM, not per-query care.

A "tenant" is a local profile, not a network identity (ADR-008): no auth, one DB,
enforced `tenant_id`. The `do_orm_execute` listener below applies a tenant predicate
to EVERY select touching a tenant-scoped entity (covers custom repository methods and
relationship loads, not just `BaseRepository`), reading the active tenant from
`session.info["tenant_id"]`.
"""
from __future__ import annotations

from sqlalchemy import ForeignKey, String, Text, event
from sqlalchemy.orm import (
    Mapped,
    ORMExecuteState,
    Session,
    mapped_column,
    with_loader_criteria,
)

from backend.models.base import Base, generate_uuid, utcnow

# session.info key holding the active tenant. Plain string so this module needs no
# dependency on services/tenancy (which would create an import cycle).
TENANT_INFO_KEY = "tenant_id"


class Tenant(Base):
    """A local career profile. Shared code/templates live outside this scope."""

    __tablename__ = "tenants"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=generate_uuid)
    name: Mapped[str] = mapped_column(Text, nullable=False, default="default")
    created_at: Mapped[str] = mapped_column(String(32), default=utcnow)


class TenantScopedMixin:
    """Marker + `tenant_id` FK for tenant-owned tables.

    Subclassing this is what makes the central guard (BaseRepository) and the
    auto-filter (below) treat a model as tenant-scoped.
    """

    tenant_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("tenants.id"), nullable=False, index=True
    )


@event.listens_for(Session, "before_flush")
def _inject_tenant_on_insert(session: Session, flush_context: object, instances: object) -> None:
    """Stamp the active tenant on any new tenant-scoped row before insert.

    Covers direct ``session.add(Model(...))`` (not just BaseRepository.create), so a
    new scoped row can never be written tenant-less when a tenant is in scope.
    """
    tenant_id = session.info.get(TENANT_INFO_KEY)
    if tenant_id is None:
        return
    for obj in session.new:
        if isinstance(obj, TenantScopedMixin) and getattr(obj, "tenant_id", None) is None:
            obj.tenant_id = tenant_id


@event.listens_for(Session, "do_orm_execute")
def _apply_tenant_filter(state: ORMExecuteState) -> None:
    """Auto-scope every ORM SELECT of a tenant-owned entity to the active tenant.

    When no tenant is in scope we do NOT filter here — `BaseRepository` raises on the
    explicit guard path, and non-request ORM use (migrations run raw SQL) stays usable.
    Opt out for a deliberate cross-tenant read (12.15 aggregation) with
    ``.execution_options(skip_tenant_filter=True)``.
    """
    # Eager loads inherit the parent statement's criteria (include_aliases=True). We
    # skip column/relationship sub-loads: a lazy load to a scoped child is reachable
    # only via a parent already scoped to the tenant, so no cross-tenant child surfaces
    # under the single-profile model. Revisit if cross-tenant relationships are added.
    if not state.is_select or state.is_column_load or state.is_relationship_load:
        return
    if state.execution_options.get("skip_tenant_filter"):
        return
    tenant_id = state.session.info.get(TENANT_INFO_KEY)
    if tenant_id is None:
        return
    state.statement = state.statement.options(
        with_loader_criteria(
            TenantScopedMixin,
            lambda cls: cls.tenant_id == tenant_id,
            include_aliases=True,
        )
    )
