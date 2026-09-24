from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    API_V1_BASE_URL: str = "/api/v1"
    DATABASE_URL: str = "postgresql+psycopg://accessory_validator:accessory_validator@localhost:5432/accessory_validator"

    APP_ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT_STRING: str = "%(levelname)s  [%(name)s] %(message)s"


settings = Settings()
