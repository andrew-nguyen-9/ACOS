from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api.errors import install_error_handlers
from backend.observability import TimingMiddleware
from backend.config import get_settings
from backend.database import init_db, seed_system_config, SessionLocal
from backend.logging_config import configure_logging
from backend.api.v1.routes.application import router as application_router
from backend.api.v1.routes.copilot import router as copilot_router
from backend.api.v1.routes.cover_letter import router as cover_letter_router
from backend.api.v1.routes.health import router as health_router
from backend.api.v1.routes.ingestion import router as ingestion_router
from backend.api.v1.routes.learning import router as learning_router
from backend.api.v1.routes.questions import router as questions_router
from backend.api.v1.routes.rag import router as rag_router
from backend.api.v1.routes.resume import router as resume_router
from backend.api.v1.routes.optimization import router as optimization_router
from backend.api.v1.routes.settings import router as settings_router
from backend.api.v1.routes.strategy import router as strategy_router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    settings = get_settings()
    configure_logging(settings.log_level)
    init_db()
    with SessionLocal() as session:
        seed_system_config(session)
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
    app.add_middleware(TimingMiddleware)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:1420",   # Tauri dev server
            "tauri://localhost",       # Tauri v2 production (macOS)
            "https://tauri.localhost", # Tauri v2 production (Windows)
        ],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health_router, prefix="/api/v1")
    app.include_router(ingestion_router, prefix="/api/v1")
    app.include_router(rag_router, prefix="/api/v1")
    app.include_router(resume_router, prefix="/api/v1")
    app.include_router(cover_letter_router, prefix="/api/v1")
    app.include_router(questions_router, prefix="/api/v1")
    app.include_router(application_router, prefix="/api/v1")
    app.include_router(learning_router, prefix="/api/v1")
    app.include_router(copilot_router, prefix="/api/v1")
    app.include_router(optimization_router, prefix="/api/v1")
    app.include_router(settings_router, prefix="/api/v1")
    app.include_router(strategy_router, prefix="/api/v1")

    return app


app = create_app()
