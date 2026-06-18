from sqlalchemy import text, inspect

from backend.models.base import Base


def test_all_tables_created(test_engine):
    inspector = inspect(test_engine)
    tables = inspector.get_table_names()
    expected = [
        "applications",
        "application_timeline",
        "answers",
        "documents",
        "experience_bullets",
        "experience_skills",
        "experiences",
        "generation_logs",
        "ingestion_logs",
        "knowledge_graph_edges",
        "knowledge_graph_nodes",
        "outcome_signals",
        "project_skills",
        "projects",
        "questions",
        "resumes",
        "resume_templates",
        "skill_evidence",
        "skills",
        "system_config",
        "writing_profiles",
    ]
    for table in expected:
        assert table in tables, f"Missing table: {table}"


def test_database_executes_query(test_engine):
    with test_engine.connect() as conn:
        result = conn.execute(text("SELECT 1"))
        assert result.scalar() == 1


def test_foreign_keys_enabled(test_session):
    result = test_session.execute(text("PRAGMA foreign_keys")).scalar()
    assert result == 1


def test_wal_mode_is_memory_for_in_memory_db(test_session):
    # In-memory SQLite always uses "memory" journal mode.
    # WAL mode is configured for file-based DBs via our connect event listener.
    result = test_session.execute(text("PRAGMA journal_mode")).scalar()
    assert result == "memory"
