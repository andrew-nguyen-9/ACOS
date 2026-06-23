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
    # 12.5 calibration — sane defaults for a 16GB M1; override via ACOS_ env.
    ollama_num_thread: int = 4  # pin to performance-core count
    ollama_keep_alive: str = "1h"  # hold the generator warm (avoid idle cold starts)

    # Models
    default_model: str = "qwen3:8b"
    embedding_model: str = "nomic-embed-text"

    # 12.8 Spike A — structured output (Ollama `format` = JSON Schema) on the
    # JSON-extraction routes. Default off (spec called this ENABLE_GBNF; renamed
    # because Ollama uses JSON-Schema `format`, not GBNF grammar files).
    enable_structured_output: bool = False

    # 14.3 (ADR-013) — optional at-rest field encryption. OFF by default. Threat
    # model is local-disk theft as defense-in-depth over FileVault, NOT a
    # multi-user/network boundary. Needs the `cryptography` extra
    # (requirements-encryption.txt) + ACOS_ENCRYPTION_KEY when enabled.
    enable_encrypted_storage: bool = False

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
