import asyncio
from typing import Any, Literal, Mapping, Sequence

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


class LiteLLMConfig(ChatConfig):
    model_config = SettingsConfigDict(env_prefix="LITELLM_")


class _ContentPart(BaseModel):
    model_config = ConfigDict(strict=True)

    type: str
    text: str | None = None
    refusal: str | None = None


class _OutputItem(BaseModel):
    model_config = ConfigDict(strict=True)

    type: str
    role: str | None = None
    content: list[_ContentPart] | None = None


class _Response(BaseModel):
    model_config = ConfigDict(strict=True)

    object: Literal["response"]
    status: str
    output: list[_OutputItem]
    model: str | None = None
    error: dict[str, Any] | None = None


def _decode(data: str | bytes) -> _Response:
    try:
        return _Response.model_validate_json(data)
    except ValidationError:
        raise LLMResponseError("Invalid Responses API response") from None


def _text(response: _Response) -> str:
    if response.status != "completed" or response.error is not None:
        raise LLMResponseError("Incomplete model response")
    text_parts = []
    for item in response.output:
        if item.type != "message":
            continue
        for part in item.content or []:
            if part.type == "refusal" and part.refusal:
                raise LLMResponseError("The model refused the request")
            if part.type == "output_text" and part.text:
                text_parts.append(part.text)
    if not text_parts:
        raise LLMResponseError("Empty model response")
    return "\n".join(text_parts)


def _error_body(response: httpx.Response) -> dict[str, Any]:
    try:
        body = response.json()
    except ValueError:
        return {}
    error = body.get("error", {}) if isinstance(body, dict) else {}
    return error if isinstance(error, dict) else {}


class LiteLLMClient:
    """Text generation through LiteLLM Proxy's Responses API endpoint."""

    def __init__(
        self,
        http_client: httpx.AsyncClient,
        config: ChatConfig | None = None,
    ) -> None:
        self._http = http_client
        self._config = config if config is not None else LiteLLMConfig.from_env()

    @property
    def config(self) -> ChatConfig:
        return self._config

    def _model_not_found(self, response: httpx.Response) -> bool:
        error = _error_body(response)
        if (
            response.status_code in (400, 404)
            and error.get("code") == "model_not_found"
        ):
            return True
        message = str(error.get("message", "")).lower()
        # LiteLLM uses HTTP 400 for unknown proxy model aliases.
        return (
            response.status_code == 400
            and "invalid model name passed in model=" in message
        )

    @staticmethod
    def _request(
        prompt: str,
        instructions: str,
        config: ChatConfig,
        model: str,
        tools: Sequence[Mapping[str, Any]],
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "model": model,
            "input": prompt,
            "store": False,
        }
        if instructions:
            payload["instructions"] = instructions
        if tools:
            payload["tools"] = [dict(tool) for tool in tools]
        if config.temperature is not None:
            payload["temperature"] = config.temperature
        if config.max_tokens is not None:
            payload["max_output_tokens"] = config.max_tokens
        headers = {"Accept": "application/json"}
        if config.api_key is not None:
            headers["Authorization"] = f"Bearer {config.api_key.get_secret_value()}"
        return {
            "url": f"{str(config.base_url).rstrip('/')}/responses",
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
        tools: Sequence[Mapping[str, Any]] = (),
    ) -> LLMResponse:
        selected = config if config is not None else self.config
        for model in selected.models:
            try:
                async with asyncio.timeout(selected.timeout_seconds):
                    response = await self._http.post(
                        **self._request(prompt, instructions, selected, model, tools)
                    )
            except (TimeoutError, httpx.TimeoutException):
                raise LLMTimeoutError("LLM request timed out") from None
            except httpx.RequestError:
                raise LLMError("Could not reach the LLM service") from None
            if self._model_not_found(response):
                continue
            self._check_status(response)
            result = _decode(response.content)
            content = _text(result)
            return LLMResponse(content, result.model or model, result.status)
        raise ModelsNotFoundError(selected.models)
