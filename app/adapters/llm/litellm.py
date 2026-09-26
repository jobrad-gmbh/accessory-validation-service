import asyncio
from typing import Any, Literal, Mapping, Sequence

import httpx
from pydantic import BaseModel, ConfigDict, Field, ValidationError
from pydantic_settings import SettingsConfigDict

from app.adapters.llm.client import LLMRequestSpec, LLMResponse, LLMSource, LLMUsage
from app.adapters.llm.config import LLMClientConfig
from app.adapters.llm.errors import (
    LLMError,
    LLMResponseError,
    LLMTimeoutError,
    ModelsNotFoundError,
    UnsupportedLLMToolError,
)


class LiteLLMConfig(LLMClientConfig):
    model_config = SettingsConfigDict(env_prefix="LITELLM_")


class _ContentPart(BaseModel):
    model_config = ConfigDict(strict=True)

    type: str
    text: str | None = None
    refusal: str | None = None
    annotations: list[dict[str, Any]] = Field(default_factory=list)


class _OutputItem(BaseModel):
    model_config = ConfigDict(strict=True)

    type: str
    role: str | None = None
    content: list[_ContentPart] | None = None


class _Usage(BaseModel):
    model_config = ConfigDict(strict=True)

    input_tokens: int | None = None
    output_tokens: int | None = None
    total_tokens: int | None = None


class _Response(BaseModel):
    model_config = ConfigDict(strict=True)

    object: Literal["response"]
    status: str
    output: list[_OutputItem]
    model: str | None = None
    error: dict[str, Any] | None = None
    usage: _Usage | None = None


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


def _tool_calls(response: _Response) -> tuple[str, ...]:
    return tuple(item.type for item in response.output if item.type.endswith("_call"))


def _sources(response: _Response) -> tuple[LLMSource, ...]:
    sources: list[LLMSource] = []
    seen_urls: set[str] = set()
    for item in response.output:
        for part in item.content or []:
            for annotation in part.annotations:
                if annotation.get("type") != "url_citation":
                    continue
                url = annotation.get("url")
                if not isinstance(url, str) or not url or url in seen_urls:
                    continue
                title = annotation.get("title")
                sources.append(
                    LLMSource(
                        url=url,
                        title=title if isinstance(title, str) and title else None,
                    )
                )
                seen_urls.add(url)
    return tuple(sources)


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
        config: LLMClientConfig | None = None,
    ) -> None:
        self._http = http_client
        self._config = config if config is not None else LiteLLMConfig.from_env()

    @property
    def config(self) -> LLMClientConfig:
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
        config: LLMClientConfig,
        model: str,
        tools: Sequence[Mapping[str, Any]],
        tool_choice: str | Mapping[str, Any] | None,
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
        if tool_choice is not None:
            payload["tool_choice"] = (
                dict(tool_choice) if isinstance(tool_choice, Mapping) else tool_choice
            )
        if config.temperature is not None:
            payload["temperature"] = config.temperature
        if config.max_tokens is not None:
            payload["max_output_tokens"] = config.max_tokens
        if config.reasoning_effort is not None:
            payload["reasoning"] = {"effort": config.reasoning_effort}
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
    def _check_status(
        response: httpx.Response,
        model: str,
        tools: Sequence[Mapping[str, Any]],
    ) -> None:
        if not response.is_success:
            error = _error_body(response)
            message = str(error.get("message", "")).lower()
            requested_tool_types = {
                str(tool.get("type", "")) for tool in tools if tool.get("type")
            }
            unsupported = any(
                phrase in message
                for phrase in (
                    "not supported",
                    "does not support",
                    "unsupported tool",
                    "unsupported_tools",
                )
            )
            error_parameter = str(error.get("param", "")).lower()
            names_web_search = "web_search" in message or "web search" in message
            names_tool_field = error_parameter in {"tools", "tool_choice"} or any(
                field in message for field in ("tool_choice", "tools", "tool use")
            )
            if requested_tool_types in (
                {"web_search"},
                {"openrouter:web_search"},
            ) and unsupported and (
                names_web_search or names_tool_field
            ):
                raise UnsupportedLLMToolError(
                    "web_search", model, status_code=response.status_code
                )
            raise LLMError(
                f"LLM service returned HTTP {response.status_code}",
                status_code=response.status_code,
            )

    async def generate(self, request: LLMRequestSpec) -> LLMResponse:
        selected = request.config if request.config is not None else self.config
        for model in selected.models:
            try:
                async with asyncio.timeout(selected.timeout_seconds):
                    response = await self._http.post(
                        **self._request(
                            request.prompt,
                            request.instructions,
                            selected,
                            model,
                            request.tools,
                            request.tool_choice,
                        )
                    )
            except (TimeoutError, httpx.TimeoutException):
                raise LLMTimeoutError("LLM request timed out") from None
            except httpx.RequestError:
                raise LLMError("Could not reach the LLM service") from None
            if self._model_not_found(response):
                continue
            self._check_status(response, model, request.tools)
            result = _decode(response.content)
            content = _text(result)
            return LLMResponse(
                content,
                result.model or model,
                result.status,
                _tool_calls(result),
                _sources(result),
                usage=(
                    LLMUsage(
                        input_tokens=result.usage.input_tokens,
                        output_tokens=result.usage.output_tokens,
                        total_tokens=result.usage.total_tokens,
                    )
                    if result.usage is not None
                    else None
                ),
            )
        raise ModelsNotFoundError(selected.models)
