import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api.deps import get_tenant_context
from backend.api.errors import install_error_handlers
from backend.observability import TimingMiddleware
from backend.config import get_settings
from backend.database import init_db, seed_system_config, SessionLocal
from backend.logging_config import configure_logging
from backend.recovery import (
    RECOVERY,
    ReadonlyRecoveryMiddleware,
    check_interrupted_restore,
    maybe_enter_recovery,
)
from backend.api.v1.routes.application import router as application_router
from backend.api.v1.routes.auth import router as auth_router
from backend.api.v1.routes.bridge import bridge_router, pairing_router
from backend.api.v1.routes.backup import router as backup_router
from backend.api.v1.routes.briefing import router as briefing_router
from backend.api.v1.routes.copilot import router as copilot_router
from backend.api.v1.routes.flywheel import router as flywheel_router
from backend.api.v1.routes.cover_letter import router as cover_letter_router
from backend.api.v1.routes.health import router as health_router
from backend.api.v1.routes.ingestion import router as ingestion_router
from backend.api.v1.routes.learning import router as learning_router
from backend.api.v1.routes.maintenance import router as maintenance_router
from backend.api.v1.routes.observability import router as observability_router
from backend.api.v1.routes.onboarding import router as onboarding_router
from backend.api.v1.routes.ollama import router as ollama_router
from backend.api.v1.routes.questions import router as questions_router
from backend.api.v1.routes.rag import router as rag_router
from backend.api.v1.routes.resume import router as resume_router
from backend.api.v1.routes.optimization import router as optimization_router
from backend.api.v1.routes.settings import router as settings_router
from backend.api.v1.routes.strategy import router as strategy_router


def _verify_audit_on_startup() -> None:
    """Enforced-policy audit chain check (ADR-016 §4). Best-effort: never block
    startup, but log a prominent warning if any tenant's chain is broken."""
    try:
        from backend.repositories.system_config import SystemConfigRepository
        from backend.services import audit

        with SessionLocal() as session:
            policy = SystemConfigRepository(session).get_value("audit_policy", default="enforced")
            if policy != "enforced":
                return
            broken = audit.verify_all_chains(session)
            if broken:
                logging.getLogger(__name__).warning(
                    "AUDIT TAMPER DETECTED: chain broken for tenant(s) %s "
                    "(ADR-016 enforced policy)", broken,
                )
    except Exception:
        logging.getLogger(__name__).exception("audit startup verification failed")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    settings = get_settings()
    configure_logging(settings.log_level)
    # Cheap corruption probe (11.4): a corrupt DB (or a restore that died mid-swap)
    # enters read-only recovery instead of crashing, so /recovery/status +
    # /backup/restore stay reachable.
    from pathlib import Path

    backups_dir = Path(settings.db_path).parent / "backups"
    try:
        init_db()
        with SessionLocal() as session:
            degraded = maybe_enter_recovery(session)
        check_interrupted_restore(backups_dir)
        if not degraded and not RECOVERY.readonly:
            with SessionLocal() as session:
                seed_system_config(session)
            # 16.3 (ADR-016): in `enforced` policy, verify the audit chain on startup
            # and warn loudly on tamper — never silently accept corruption.
            _verify_audit_on_startup()
    except Exception:  # init_db itself can fail on a corrupt file
        logging.getLogger(__name__).exception("startup failed")
        RECOVERY.enter("startup failed (see logs)")
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="ACOS API",
        description="AI Career Operating System — local-first career intelligence",
        version=settings.app_version,
        lifespan=lifespan,
    )

    install_error_handlers(app)
    app.add_middleware(ReadonlyRecoveryMiddleware)
    app.add_middleware(TimingMiddleware)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:1420",   # Tauri dev server
            "tauri://localhost",       # Tauri v2 production (macOS)
            "https://tauri.localhost", # Tauri v2 production (Windows)
        ],
        # 17.1 (ADR-019): allow the paired browser extension to reach the loopback
        # bridge. The sideloaded extension id isn't known ahead of time, so the
        # scheme is matched by regex; the one-time X-Bridge-Token is the actual
        # access gate (default-closed), not the origin.
        allow_origin_regex=r"^(chrome-extension|moz-extension)://.*$",
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Tenant-scoped routers carry the TenantContext dependency (12.14, ADR-008): an
    # explicit per-route contract on top of the session-boundary guard. System /
    # operational routers (health, settings, maintenance, backup) are tenant-free.
    tenant_dep = [Depends(get_tenant_context)]

    app.include_router(health_router, prefix="/api/v1")
    # Auth (16.1, ADR-014): unauthenticated by design — establishes the session that
    # gates every tenant-scoped router below.
    app.include_router(auth_router, prefix="/api/v1")
    # Bridge (17.1, ADR-019): pairing-token mint is authed (tenant-scoped); ping +
    # capture are gated by X-Bridge-Token (the paired extension), not a bearer session.
    app.include_router(pairing_router, prefix="/api/v1")  # tenant dep declared on the router
    app.include_router(bridge_router, prefix="/api/v1")
    app.include_router(ingestion_router, prefix="/api/v1", dependencies=tenant_dep)
    app.include_router(rag_router, prefix="/api/v1", dependencies=tenant_dep)
    app.include_router(resume_router, prefix="/api/v1", dependencies=tenant_dep)
    app.include_router(cover_letter_router, prefix="/api/v1", dependencies=tenant_dep)
    app.include_router(questions_router, prefix="/api/v1", dependencies=tenant_dep)
    app.include_router(application_router, prefix="/api/v1", dependencies=tenant_dep)
    app.include_router(learning_router, prefix="/api/v1", dependencies=tenant_dep)
    # tenant-scoped: 14.2 drift/snapshot writes a tenant-owned Metric, so the
    # session needs an active tenant (reads stay scoped to it too).
    app.include_router(observability_router, prefix="/api/v1", dependencies=tenant_dep)
    app.include_router(copilot_router, prefix="/api/v1", dependencies=tenant_dep)
    app.include_router(optimization_router, prefix="/api/v1", dependencies=tenant_dep)
    app.include_router(settings_router, prefix="/api/v1")
    app.include_router(strategy_router, prefix="/api/v1", dependencies=tenant_dep)
    app.include_router(briefing_router, prefix="/api/v1", dependencies=tenant_dep)
    app.include_router(maintenance_router, prefix="/api/v1")
    app.include_router(backup_router, prefix="/api/v1")
    app.include_router(flywheel_router, prefix="/api/v1", dependencies=tenant_dep)
    app.include_router(onboarding_router, prefix="/api/v1", dependencies=tenant_dep)
    app.include_router(ollama_router, prefix="/api/v1")

    return app


app = create_app()
