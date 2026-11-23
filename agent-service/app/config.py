"""Configuration for the agent service."""

import os
from functools import lru_cache
from pathlib import Path

from pydantic import Field, ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent
DEFAULT_ENV_FILES = (BASE_DIR / ".env",)


class Settings(BaseSettings):
    """Runtime settings loaded from environment variables and .env files."""

    model_config = SettingsConfigDict(extra="ignore", case_sensitive=False)

    nest_base_url: str = "http://localhost:3001"
    google_api_key: str = Field(min_length=1)
    chat_model: str
    embedding_model: str
    chroma_dir: Path = BASE_DIR / "data" / "chroma"
    knowledge_dir: Path = BASE_DIR / "knowledge"
    tavily_api_key: str = Field(min_length=1)
    retrieval_top_k: int = Field(default=4, gt=0)
    http_timeout_seconds: float = Field(default=10.0, gt=0)
    llm_temperature: float = Field(ge=0, le=2)
    llm_timeout_seconds: float = Field(default=45.0, gt=0)
    llm_max_retries: int = Field(default=2, ge=0)


def _env_files() -> tuple[Path, ...]:
    override = os.getenv("AGENT_ENV_FILE")
    return (Path(override),) if override else DEFAULT_ENV_FILES


@lru_cache
def get_settings() -> Settings:
    """Load settings, failing clearly when the LLM key is absent."""

    try:
        settings = Settings(_env_file=_env_files())
    except ValidationError as exc:
        missing_google_key = any(
            error["loc"] and error["loc"][0] == "google_api_key" for error in exc.errors()
        )
        if missing_google_key:
            raise RuntimeError("GOOGLE_API_KEY is required to start the agent service") from exc
        raise
    if not settings.google_api_key.strip():
        raise RuntimeError("GOOGLE_API_KEY is required to start the agent service")
    return settings
