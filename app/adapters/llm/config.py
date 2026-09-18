from typing import Annotated, Any, Self

from pydantic import Field, HttpUrl, SecretStr, StringConstraints, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


ModelName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class LLMConfig(BaseSettings):
    """Explicit values override environment defaults. Never invent endpoint/model names."""

    model_config = SettingsConfigDict(
        env_prefix="LLM_",
        env_file=".env",
        extra="ignore",
        frozen=True,
    )

    base_url: HttpUrl
    api_key: SecretStr | None = None
    models: tuple[ModelName, ...] = Field(min_length=1)
    timeout_seconds: float = Field(default=60, gt=0, allow_inf_nan=False)

    @classmethod
    def from_env(cls) -> Self:
        values: dict[str, Any] = {}
        return cls(**values)

    @model_validator(mode="after")
    def validate_url(self) -> Self:
        if self.base_url.username or self.base_url.password:
            raise ValueError("Use api_key instead of credentials in base_url")
        if self.base_url.query or self.base_url.fragment:
            raise ValueError("base_url must not contain a query or fragment")
        return self

    def with_overrides(self, **changes: object) -> Self:
        """Return a validated copy without changing this client's defaults."""
        unknown = changes.keys() - type(self).model_fields.keys()
        if unknown:
            raise ValueError(f"Unknown LLM settings: {', '.join(sorted(unknown))}")
        return type(self).model_validate({**self.model_dump(), **changes})


class ChatConfig(LLMConfig):
    temperature: float | None = Field(default=None, ge=0, le=2, allow_inf_nan=False)
    max_tokens: int | None = Field(default=None, gt=0, strict=True)
