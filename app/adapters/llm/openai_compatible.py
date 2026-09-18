import asyncio
from typing import Any

import httpx
from pydantic import BaseModel, ConfigDict, ValidationError
from pydantic_settings import SettingsConfigDict

from app.adapters.llm.client import LLMResponse
from app.adapters.llm.config import ChatConfig
from app.adapters.llm.errors import (
    LLMError,
    LLMResponseError,
    LLMTimeoutError,
    ModelsNotFoundError,
)


class OpenAIConfig(ChatConfig):
    model_config = SettingsConfigDict(env_prefix="OPENAI_")


class _Message(BaseModel):
    model_config = ConfigDict(strict=True)
    content: str | None = None
    refusal: str | None = None
    tool_calls: list[Any] | None = None


class _Choice(BaseModel):
    model_config = ConfigDict(strict=True)
    index: int = 0
    message: _Message | None = None
    delta: _Message | None = None
    finish_reason: str | None = None


class _Completion(BaseModel):
    model_config = ConfigDict(strict=True)
    choices: list[_Choice]
    model: str | None = None


def _decode(data: str | bytes) -> _Completion:
    try:
        return _Completion.model_validate_json(data)
    except ValidationError:
        raise LLMResponseError("Invalid chat completion response") from None


def _text(message: _Message | None) -> str:
    if message is None:
        raise LLMResponseError("Missing message content")
    if message.refusal:
        raise LLMResponseError("The model refused the request")
    if message.tool_calls:
        raise LLMResponseError("Tool calls are not supported by this text client")
    return message.content or ""


def _choice(completion: _Completion) -> _Choice:
    if len(completion.choices) != 1 or completion.choices[0].index != 0:
        raise LLMResponseError("Expected one completion choice")
    return completion.choices[0]


def _error_body(response: httpx.Response) -> dict[str, Any]:
    try:
        body = response.json()
    except ValueError:
        return {}
    error = body.get("error", {}) if isinstance(body, dict) else {}
    return error if isinstance(error, dict) else {}


class OpenAICompatibleClient:
    """Text chat completions. The caller owns and closes the HTTP client."""

    def __init__(
        self,
        http_client: httpx.AsyncClient,
        config: ChatConfig | None = None,
    ) -> None:
        self._http = http_client
        self._config = config if config is not None else OpenAIConfig.from_env()

    @property
    def config(self) -> ChatConfig:
        return self._config

    def _model_not_found(self, response: httpx.Response) -> bool:
        # A generic 404 may mean a bad URL. It must identify the model explicitly.
        return (
            response.status_code in (400, 404)
            and _error_body(response).get("code") == "model_not_found"
        )

    def _request(
        self,
        prompt: str,
        instructions: str,
        config: ChatConfig,
        model: str
    ) -> dict[str, Any]:
        messages = []
        if instructions:
            messages.append({"role": "system", "content": instructions})
        messages.append({"role": "user", "content": prompt})
        payload: dict[str, Any] = {
            "model": model,
            "messages": messages,
        }
        if config.temperature is not None:
            payload["temperature"] = config.temperature
        if config.max_tokens is not None:
            payload["max_tokens"] = config.max_tokens
        headers = {"Accept": "application/json"}
        if config.api_key is not None:
            headers["Authorization"] = f"Bearer {config.api_key.get_secret_value()}"
        return {
            "url": f"{str(config.base_url).rstrip('/')}/chat/completions",
            "headers": headers,
            "json": payload,
            "timeout": httpx.Timeout(config.timeout_seconds),
            "follow_redirects": False,
        }

    @staticmethod
    def _check_status(response: httpx.Response) -> None:
        if not response.is_success:
            raise LLMError(
                f"LLM service returned HTTP {response.status_code}",
                status_code=response.status_code,
            )

    async def generate(
        self,
        prompt: str,
        *,
        instructions: str = "",
        config: ChatConfig | None = None,
    ) -> LLMResponse:
        selected = config if config is not None else self.config
        for model in selected.models:
            try:
                async with asyncio.timeout(selected.timeout_seconds):
                    response = await self._http.post(
                        **self._request(
                            prompt, instructions, selected, model
                        )
                    )
            except (TimeoutError, httpx.TimeoutException):
                raise LLMTimeoutError("LLM request timed out") from None
            except httpx.RequestError:
                raise LLMError("Could not reach the LLM service") from None
            if self._model_not_found(response):
                continue
            self._check_status(response)
            completion = _decode(response.content)
            choice = _choice(completion)
            content = _text(choice.message)
            if choice.finish_reason != "stop" or not content:
                raise LLMResponseError("Empty or incomplete completion")
            return LLMResponse(content, completion.model or model, choice.finish_reason)
        raise ModelsNotFoundError(selected.models)
