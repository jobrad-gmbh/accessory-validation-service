from pydantic import Field, HttpUrl, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    API_V1_BASE_URL: str = "/api/v1"

    # LLM support is optional for validations that do not use it. A client must
    # still receive explicit values when it is constructed.
    LLM_BASE_URL: HttpUrl | None = None
    LLM_API_KEY: SecretStr | None = None
    LLM_MODEL: str | None = Field(default=None, min_length=1)
    LLM_TIMEOUT_SECONDS: float = Field(default=60, gt=0, allow_inf_nan=False)

    APP_ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT_STRING: str = "%(levelname)s  [%(name)s] %(message)s"


settings = Settings()
