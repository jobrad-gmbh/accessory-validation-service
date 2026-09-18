import httpx
from pydantic_settings import SettingsConfigDict

from app.adapters.llm.config import ChatConfig
from app.adapters.llm.openai_compatible import OpenAICompatibleClient, _error_body


class LiteLLMConfig(ChatConfig):
    model_config = SettingsConfigDict(env_prefix="LITELLM_")


class LiteLLMClient(OpenAICompatibleClient):
    """LiteLLM Proxy client, using its OpenAI-compatible chat endpoint."""

    def __init__(
        self,
        http_client: httpx.AsyncClient,
        config: ChatConfig | None = None,
    ) -> None:
        super().__init__(
            http_client,
            config if config is not None else LiteLLMConfig.from_env(),
        )

    def _model_not_found(self, response: httpx.Response) -> bool:
        if super()._model_not_found(response):
            return True
        error = _error_body(response)
        message = str(error.get("message", "")).lower()
        # LiteLLM uses HTTP 400 for unknown proxy model aliases.
        return (
            response.status_code == 400
            and "invalid model name passed in model=" in message
        )
