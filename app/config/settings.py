from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    API_V1_BASE_URL: str = "/api/v1"
    APP_ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "%(levelname)s [%(name)s] %(message)s"

    SEARXNG_BASE_URL: str = "http://127.0.0.1:8080"
    SEARXNG_TIMEOUT_SECONDS: float = Field(default=15.0, gt=0)
    SEARXNG_RESULT_LIMIT: int = Field(default=5, ge=1, le=20)

    LLM_BASE_URL: str = "http://127.0.0.1:4000/v1"
    LLM_API_KEY: str | None = None
    LLM_MODEL: str | None = None
    LLM_TIMEOUT_SECONDS: float = Field(default=60.0, gt=0)


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
