from pydantic import computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict
{%- if 'postgresql' in values.features %}
from pydantic.networks import PostgresDsn
{%- endif %}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
    )
    API_V1_BASE_URL: str = "/api/v1"

{%- if 'postgresql' in values.features %}
    DATABASE_HOST: str = "localhost"
    DATABASE_USER: str = "postgres"
    DATABASE_PASSWORD: str = "postgres"
    DATABASE_PORT: int = 5432
    DATABASE_NAME: str = "${{ values.projectNameKebab }}"
{%- endif %}

{%- if 'kafka' in values.features %}
    KAFKA_BOOTSTRAP_SERVERS: str = "localhost:9092"
{%- endif %}

    APP_ENVIRONMENT: str = "development"

    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "%(levelname)s  [%(name)s] %(message)s"

{%- if 'postgresql' in values.features %}
    @computed_field  # type: ignore[prop-decorator]
    @property
    def SQLALCHEMY_DATABASE_URI(self) -> str:
        return str(
            PostgresDsn(
                f"postgresql+psycopg://{self.DATABASE_USER}:{self.DATABASE_PASSWORD}@{self.DATABASE_HOST}/{self.DATABASE_NAME}"
            )
        )
{%- endif %}


settings = Settings()
