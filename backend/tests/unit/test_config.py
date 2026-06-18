from backend.config import Settings, get_settings


def test_default_settings_have_correct_values():
    s = Settings()
    assert s.db_path == "./database/acos.db"
    assert s.chroma_path == "./database/chroma"
    assert s.ollama_base_url == "http://localhost:11434"
    assert s.default_model == "qwen3:8b"
    assert s.embedding_model == "nomic-embed-text"
    assert s.learning_trigger_count == 5
    assert s.log_level == "INFO"
    assert s.app_version == "0.1.0"
    assert s.debug is False


def test_db_url_property_returns_sqlite_url():
    s = Settings(db_path="./test.db")
    assert s.db_url == "sqlite:///./test.db"


def test_env_prefix_is_acos(monkeypatch):
    monkeypatch.setenv("ACOS_DEFAULT_MODEL", "llama3:8b")
    s = Settings()
    assert s.default_model == "llama3:8b"


def test_get_settings_is_cached():
    s1 = get_settings()
    s2 = get_settings()
    assert s1 is s2
