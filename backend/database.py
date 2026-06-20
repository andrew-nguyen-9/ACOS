from collections.abc import Generator

from sqlalchemy import create_engine, event, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

import backend.models  # noqa: F401 — registers all models with Base.metadata
from backend.models.base import Base
from backend.config import get_settings


def _enable_wal_and_fk(dbapi_connection: object, _: object) -> None:
    cursor = dbapi_connection.cursor()  # type: ignore[union-attr]
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


def build_engine(db_url: str | None = None) -> Engine:
    url = db_url or get_settings().db_url
    engine = create_engine(
        url,
        connect_args={"check_same_thread": False},
        echo=get_settings().debug,
    )
    event.listen(engine, "connect", _enable_wal_and_fk)
    return engine


# Module-level engine and session factory (replaced in tests via conftest)
engine = build_engine()
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


def init_db() -> None:
    """Create all tables. Safe to call repeatedly (no-op if tables exist)."""
    Base.metadata.create_all(bind=engine)


def get_session() -> Generator[Session, None, None]:
    """FastAPI dependency that yields a database session per request."""
    with SessionLocal() as session:
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise


def seed_system_config(session: Session) -> None:
    """Insert default system_config rows if they don't exist."""
    from backend.models.system_config import SystemConfig

    defaults = [
        ("default_model", "qwen3:8b", "Default Ollama model for generation"),
        ("embedding_model", "nomic-embed-text", "Ollama model for embeddings"),
        ("learning_trigger_count", "5", "Applications before learning refresh"),
        ("ats_keyword_weight", "0.35", "ATS scoring: keyword match weight"),
        ("ats_skill_weight", "0.25", "ATS scoring: skill match weight"),
        ("ats_experience_weight", "0.20", "ATS scoring: experience match weight"),
        ("ats_industry_weight", "0.10", "ATS scoring: industry match weight"),
        ("ats_education_weight", "0.10", "ATS scoring: education match weight"),
        ("github_username", "", "GitHub username for profile integration"),
        ("onboarding_complete", "false", "Whether the first-run wizard has been completed"),
    ]
    for key, value, description in defaults:
        exists = session.get(SystemConfig, key)
        if not exists:
            session.add(SystemConfig(key=key, value=value, description=description))
    session.commit()
