import asyncio
import json
import math
from typing import Literal

import httpx
import pytest
from pydantic import BaseModel, ConfigDict, HttpUrl, SecretStr, ValidationError

from app.adapters.llm import (
    LiteLLMClient,
    LiteLLMSettings,
    LlmError,
    LlmHttpError,
    LlmResponseError,
    LlmTimeoutError,
)


class Classification(BaseModel):
    model_config = ConfigDict(extra="forbid")

    answer: Literal["YES", "NO", "UNKNOWN"]
    reason_code: str


def settings() -> LiteLLMSettings:
    return LiteLLMSettings(
        base_url=HttpUrl("https://llm.example.test/v1"),
        api_key=SecretStr("secret-token"),
        model="default-model",
        timeout_seconds=5,
    )


def completion(
    content: str | None,
    *,
    finish_reason: str = "stop",
    refusal: str | None = None,
) -> dict[str, object]:
    return {
        "choices": [
            {
                "finish_reason": finish_reason,
                "message": {"content": content, "refusal": refusal},
            }
        ]
    }


@pytest.mark.asyncio
async def test_sends_request_and_returns_validated_content() -> None:
    captured_request: httpx.Request | None = None

    async def handler(request: httpx.Request) -> httpx.Response:
        nonlocal captured_request
        captured_request = request
        return httpx.Response(
            200,
            json=completion('{"answer":"YES","reason_code":"MATCH"}'),
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
        client = LiteLLMClient(settings(), http)
        result = await client.generate(
            instructions="Classify the product.",
            input="A bicycle bell",
            response_type=Classification,
        )

    assert result == Classification(answer="YES", reason_code="MATCH")
    assert captured_request is not None
    assert str(captured_request.url) == "https://llm.example.test/v1/chat/completions"
    assert captured_request.headers["Authorization"] == "Bearer secret-token"

    request_body = json.loads(captured_request.content)
    assert request_body["model"] == "default-model"
    assert request_body["messages"][1]["content"] == "A bicycle bell"
    assert "JSON Schema" in request_body["messages"][0]["content"]


@pytest.mark.asyncio
async def test_accepts_per_request_model_and_timeout_overrides() -> None:
    captured_body: dict[str, object] = {}

    async def handler(request: httpx.Request) -> httpx.Response:
        captured_body.update(json.loads(request.content))
        return httpx.Response(
            200,
            json=completion('{"answer":"NO","reason_code":"NO_MATCH"}'),
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
        client = LiteLLMClient(settings(), http)
        await client.generate(
            instructions="Classify.",
            input="A coffee mug",
            response_type=Classification,
            model="override-model",
            timeout_seconds=1,
        )

    assert captured_body["model"] == "override-model"


@pytest.mark.asyncio
@pytest.mark.parametrize("status_code", [401, 429, 503])
async def test_exposes_unsuccessful_http_status(status_code: int) -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(status_code, json={"error": "private provider details"})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
        client = LiteLLMClient(settings(), http)
        with pytest.raises(LlmHttpError) as raised:
            await client.generate(
                instructions="Classify.", input="product", response_type=Classification
            )

    assert raised.value.status_code == status_code
    assert "private provider details" not in str(raised.value)


@pytest.mark.asyncio
async def test_handles_connection_errors() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("private connection details", request=request)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
        client = LiteLLMClient(settings(), http)
        with pytest.raises(LlmError, match="Could not connect"):
            await client.generate(
                instructions="Classify.", input="product", response_type=Classification
            )


@pytest.mark.asyncio
async def test_enforces_request_timeout() -> None:
    async def handler(_: httpx.Request) -> httpx.Response:
        await asyncio.sleep(0.05)
        return httpx.Response(200)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
        client = LiteLLMClient(settings(), http)
        with pytest.raises(LlmTimeoutError, match="timed out"):
            await client.generate(
                instructions="Classify.",
                input="product",
                response_type=Classification,
                timeout_seconds=0.001,
            )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("response_body", "message"),
    [
        (b"not-json", "Invalid LLM response"),
        (json.dumps({"choices": []}).encode(), "exactly one"),
        (json.dumps(completion(None, refusal="refused")).encode(), "refused"),
        (
            json.dumps(completion("{}", finish_reason="length")).encode(),
            "incomplete",
        ),
        (json.dumps(completion("  ")).encode(), "empty content"),
        (
            json.dumps(completion('{"answer":"MAYBE","reason_code":"?"}')).encode(),
            "invalid content",
        ),
    ],
)
async def test_rejects_unusable_responses(response_body: bytes, message: str) -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=response_body)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
        client = LiteLLMClient(settings(), http)
        with pytest.raises(LlmResponseError, match=message):
            await client.generate(
                instructions="Classify.", input="product", response_type=Classification
            )


def test_loads_settings_from_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM_BASE_URL", "https://gateway.example.test/v1")
    monkeypatch.setenv("LLM_API_KEY", "top-secret")
    monkeypatch.setenv("LLM_MODEL", "configured-model")
    monkeypatch.setenv("LLM_TIMEOUT_SECONDS", "12.5")

    configured = LiteLLMSettings()  # type: ignore[call-arg]

    assert str(configured.base_url) == "https://gateway.example.test/v1"
    assert configured.model == "configured-model"
    assert configured.timeout_seconds == 12.5
    assert "top-secret" not in repr(configured)


def test_requires_a_configured_base_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("LLM_BASE_URL", raising=False)

    with pytest.raises(ValidationError, match="base_url"):
        LiteLLMSettings(model="model", _env_file=None)  # type: ignore[call-arg]


@pytest.mark.parametrize("timeout", [0, -1, math.inf, math.nan])
def test_rejects_invalid_default_timeout(timeout: float) -> None:
    with pytest.raises(ValidationError):
        LiteLLMSettings(
            base_url=HttpUrl("https://llm.example.test/v1"),
            model="model",
            timeout_seconds=timeout,
        )


@pytest.mark.asyncio
@pytest.mark.parametrize("timeout", [0, -1, math.inf, math.nan])
async def test_rejects_invalid_request_timeout(timeout: float) -> None:
    async with httpx.AsyncClient() as http:
        client = LiteLLMClient(settings(), http)
        with pytest.raises(ValueError, match="finite and positive"):
            await client.generate(
                instructions="Classify.",
                input="product",
                response_type=Classification,
                timeout_seconds=timeout,
            )
