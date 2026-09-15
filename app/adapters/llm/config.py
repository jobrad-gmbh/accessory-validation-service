from pydantic import Field, HttpUrl, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class LiteLLMSettings(BaseSettings):
    """LiteLLM Proxy defaults loaded from the LLM_* environment variables."""

    model_config = SettingsConfigDict(
        env_prefix="LLM_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        str_strip_whitespace=True,
    )

    base_url: HttpUrl
    api_key: SecretStr = SecretStr("")
    model: str = Field(min_length=1)
    timeout_seconds: float = Field(default=60, gt=0, allow_inf_nan=False)
