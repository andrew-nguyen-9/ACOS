from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="ACOS_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Database
    db_path: str = "./database/acos.db"

    # ChromaDB
    chroma_path: str = "./database/chroma"

    # Ollama
    ollama_base_url: str = "http://localhost:11434"
    ollama_timeout: int = 120

    # Models
    default_model: str = "qwen3:8b"
    embedding_model: str = "nomic-embed-text"

    # Learning
    learning_trigger_count: int = 5

    # Logging
    log_level: str = "INFO"

    # App
    app_version: str = "0.1.0"
    debug: bool = False

    @property
    def db_url(self) -> str:
        return f"sqlite:///{self.db_path}"

    @property
    def chroma_db_path(self) -> str:
        return self.chroma_path


@lru_cache
def get_settings() -> Settings:
    return Settings()
