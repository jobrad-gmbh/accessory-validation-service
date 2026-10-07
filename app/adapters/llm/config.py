from typing import Annotated, Any, Literal, Self

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    HttpUrl,
    SecretStr,
    StringConstraints,
    field_validator,
)
from pydantic_settings import BaseSettings, SettingsConfigDict


ModelName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
Models = Annotated[tuple[ModelName, ...], Field(min_length=1)]
# OpenAI's vocabulary; individual models support only a subset, and the
# provider/gateway rejects values a model does not support.
ReasoningEffort = Literal[
    "none", "minimal", "low", "medium", "high", "xhigh", "max"
]


class LLMModelSettings(BaseModel):
    """How the model is called. Unset (None) values keep the config's values."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    models: Models | None = None
    timeout_seconds: float | None = Field(default=None, gt=0, allow_inf_nan=False)
    temperature: float | None = Field(default=None, ge=0, le=2, allow_inf_nan=False)
    max_tokens: int | None = Field(default=None, gt=0, strict=True)
    reasoning_effort: ReasoningEffort | None = None


class LLMConnectionSettings(BaseModel):
    """Where the LLM API is and how to authenticate. Unset values keep the config's."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    base_url: HttpUrl | None = None
    api_key: SecretStr | None = None

    @field_validator("base_url")
    @classmethod
    def validate_base_url(cls, url: HttpUrl | None) -> HttpUrl | None:
        if url is None:
            return url
        if url.username or url.password:
            raise ValueError("Use api_key instead of credentials in base_url")
        if url.query or url.fragment:
            raise ValueError("base_url must not contain a query or fragment")
        return url
    

class LLMClientConfig(BaseSettings, LLMConnectionSettings, LLMModelSettings):
    """
    Complete client config. Explicit values override environment defaults.
    Some fields were redefined to make them required.
    """

    model_config = SettingsConfigDict(
        env_prefix="LLM_",
        env_file=".env",
        extra="ignore",
        frozen=True,
    )

    base_url: HttpUrl
    models: Models
    timeout_seconds: float = Field(default=180, gt=0, allow_inf_nan=False)

    @classmethod
    def from_env(cls) -> Self:
        values: dict[str, Any] = {}
        return cls(**values)

    def with_overrides(self, **changes: object) -> Self:
        """Return a validated copy without changing this client's defaults."""
        unknown = changes.keys() - type(self).model_fields.keys()
        if unknown:
            raise ValueError(f"Unknown LLM settings: {', '.join(sorted(unknown))}")
        return type(self).model_validate({**self.model_dump(), **changes})

    def with_settings(self, settings: LLMModelSettings) -> Self:
        """Return a copy that uses every value set in ``settings``."""
        return self.with_overrides(**settings.model_dump(exclude_none=True))
