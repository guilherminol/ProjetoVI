from functools import lru_cache
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # Database (async URL for SQLAlchemy, sync URL for Alembic)
    database_url: str  # postgresql+asyncpg://...
    postgres_user: str = "rag"
    postgres_password: str = "changeme"
    postgres_db: str = "ragdb"

    # Derived sync URL for Alembic (replaces asyncpg with psycopg2)
    @property
    def sync_database_url(self) -> str:
        return self.database_url.replace("postgresql+asyncpg://", "postgresql://")

    # Security
    admin_api_key: str  # Required — no default

    # OpenRouter / LLM
    openrouter_api_key: str  # Required — no default
    embedding_model: str = "openai/text-embedding-3-small"
    embedding_dimension: int = 1536

    @field_validator("embedding_dimension")
    @classmethod
    def dimension_must_be_1536(cls, v: int) -> int:
        if v != 1536:
            raise ValueError(
                f"embedding_dimension must be 1536 (text-embedding-3-small). "
                f"Got {v}. Changing this requires full vector re-ingestion."
            )
        return v

    # Storage
    pdf_storage_path: str = "/app/storage/pdfs"

    # JWT Auth (Phase 2)
    jwt_secret_key: str  # Required — generate with: openssl rand -hex 32
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 1440  # 24 hours

    # LLM (Phase 2)
    llm_model: str = "anthropic/claude-3-5-haiku"

    @property
    def langgraph_conn_string(self) -> str:
        """psycopg3-style connection string for LangGraph AsyncPostgresSaver."""
        return self.database_url.replace("postgresql+asyncpg://", "postgresql://")


@lru_cache
def get_settings() -> Settings:
    return Settings()
