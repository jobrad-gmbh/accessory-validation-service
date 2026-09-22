import asyncio
import json

import httpx
import pytest
from pydantic import ValidationError

from app.adapters.llm import (
    ChoiceQuestion,
    JevClient,
    JevConfig,
    JevRequest,
    LLMError,
    LLMResponseError,
    LLMTimeoutError,
    LiteLLMClient,
    LiteLLMConfig,
    ModelsNotFoundError,
    NoulQuestion,
    ScoreQuestion,
    UnsupportedLLMToolError,
)


def config(cls=LiteLLMConfig, **overrides):
    return cls(
        base_url="https://llm.example/v1", models=("first", "second"), **overrides
    )


def response(text="Hello", status="completed", *, with_tool_call=False):
    output = []
    if with_tool_call:
        output.append(
            {"type": "web_search_call", "id": "ws_123", "status": "completed"}
        )
    output.append(
        {
            "type": "message",
            "role": "assistant",
            "content": [{"type": "output_text", "text": text, "annotations": []}],
        }
    )
    return {
        "object": "response",
        "status": status,
        "model": "actual-model",
        "output": output,
    }


@pytest.mark.asyncio
async def test_generate_fallback_and_request_overrides():
    requests = []

    def handle(request):
        requests.append(request)
        if len(requests) == 1:
            return httpx.Response(
                400,
                json={"error": {"message": "Invalid model name passed in model=first"}},
            )
        return httpx.Response(200, json=response())

    async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as http:
        client = LiteLLMClient(http, config(api_key="secret"))
        override = client.config.with_overrides(
            temperature=0.2, max_tokens=50, timeout_seconds=3
        )
        result = await client.generate(
            "Hello",
            instructions="Be brief",
            config=override,
            tools=({"type": "web_search"},),
            tool_choice={"type": "web_search"},
        )
        assert result.text == "Hello"
        assert result.model == "actual-model"
        assert result.status == "completed"
        assert client.config.temperature is None
    bodies = [json.loads(r.content) for r in requests]
    assert [b["model"] for b in bodies] == ["first", "second"]
    assert bodies[-1]["temperature"] == 0.2
    assert bodies[-1]["max_output_tokens"] == 50
    assert bodies[-1]["input"] == "Hello"
    assert bodies[-1]["instructions"] == "Be brief"
    assert bodies[-1]["tools"] == [{"type": "web_search"}]
    assert bodies[-1]["tool_choice"] == {"type": "web_search"}
    assert bodies[-1]["store"] is False
    assert str(requests[-1].url) == "https://llm.example/v1/responses"
    assert requests[-1].headers["authorization"] == "Bearer secret"
    assert requests[-1].extensions["timeout"]["read"] == 3


@pytest.mark.asyncio
async def test_response_reports_tool_calls_and_citation_sources():
    body = response("Product summary", with_tool_call=True)
    body["output"][-1]["content"][0]["annotations"] = [
        {
            "type": "url_citation",
            "url": "https://manufacturer.example/product",
            "title": "Product page",
            "start_index": 0,
            "end_index": 7,
        }
    ]

    def handle(request):
        return httpx.Response(200, json=body)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as http:
        result = await LiteLLMClient(http, config()).generate("hi")

    assert result.tool_calls == ("web_search_call",)
    assert len(result.sources) == 1
    assert result.sources[0].url == "https://manufacturer.example/product"
    assert result.sources[0].title == "Product page"


@pytest.mark.asyncio
async def test_explicit_unsupported_web_search_error_is_classified():
    def handle(request):
        return httpx.Response(
            400,
            json={
                "error": {
                    "message": "Model local-model does not support web_search"
                }
            },
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as http:
        with pytest.raises(UnsupportedLLMToolError) as error:
            selected = LiteLLMConfig(
                base_url="https://llm.example/v1", models=("local-model",)
            )
            await LiteLLMClient(http, selected).generate(
                "hi", tools=({"type": "web_search"},)
            )

    assert error.value.model == "local-model"
    assert error.value.tool == "web_search"
    assert error.value.status_code == 400


@pytest.mark.asyncio
async def test_unsupported_tools_parameter_is_classified_for_web_search_request():
    def handle(request):
        return httpx.Response(
            400,
            json={
                "error": {
                    "message": "Tools are not supported for this model",
                    "param": "tools",
                }
            },
        )

    selected = LiteLLMConfig(
        base_url="https://llm.example/v1", models=("local-model",)
    )
    async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as http:
        with pytest.raises(UnsupportedLLMToolError):
            await LiteLLMClient(http, selected).generate(
                "hi", tools=({"type": "web_search"},)
            )


@pytest.mark.asyncio
async def test_exhausted_models():
    calls = []

    def handle(request):
        calls.append(json.loads(request.content)["model"])
        return httpx.Response(404, json={"error": {"code": "model_not_found"}})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as http:
        client = LiteLLMClient(http, config())
        with pytest.raises(ModelsNotFoundError) as error:
            await client.generate("hi")
    assert calls == ["first", "second"]
    assert error.value.models == ("first", "second")


@pytest.mark.asyncio
@pytest.mark.parametrize("status", [400, 401, 403, 404, 422, 429, 500, 529])
async def test_http_errors_do_not_fallback_or_leak_body(status):
    calls = []

    def handle(request):
        calls.append(request)
        return httpx.Response(status, text="sensitive provider body")

    async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as http:
        with pytest.raises(LLMError) as error:
            await LiteLLMClient(http, config()).generate("sensitive prompt")
    assert len(calls) == 1
    assert error.value.status_code == status
    assert "sensitive" not in str(error.value)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "body",
    [
        response(""),
        response("partial", "incomplete"),
        {"object": "response", "status": "completed", "output": []},
        {
            "object": "response",
            "status": "completed",
            "output": [
                {
                    "type": "message",
                    "content": [{"type": "output_text", "text": 123}],
                }
            ],
        },
        {
            "object": "response",
            "status": "completed",
            "output": [
                {
                    "type": "message",
                    "content": [{"type": "refusal", "refusal": "No"}],
                }
            ],
        },
        {
            "object": "response",
            "status": "failed",
            "output": [],
            "error": {"code": "server_error", "message": "provider detail"},
        },
    ],
)
async def test_invalid_responses(body):
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(
            lambda _: httpx.Response(200, json=body),
        )
    ) as http:
        with pytest.raises(LLMResponseError):
            await LiteLLMClient(http, config()).generate("hi")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "error,expected",
    [
        (httpx.ReadTimeout("secret"), LLMTimeoutError),
        (httpx.ConnectError("secret"), LLMError),
        (asyncio.CancelledError(), asyncio.CancelledError),
    ],
)
async def test_transport_errors_and_cancellation(error, expected):
    calls = []

    def handle(request):
        calls.append(request)
        raise error

    async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as http:
        with pytest.raises(expected):
            await LiteLLMClient(http, config()).generate("hi")
    assert len(calls) == 1


@pytest.mark.asyncio
async def test_total_generation_timeout():
    async def handle(request):
        await asyncio.sleep(1)
        return httpx.Response(200, json=response())

    async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as http:
        with pytest.raises(LLMTimeoutError):
            await LiteLLMClient(http, config(timeout_seconds=0.01)).generate("hi")


def test_env_defaults_and_explicit_values(monkeypatch):
    monkeypatch.setenv("LITELLM_BASE_URL", "https://gateway.example/v1")
    monkeypatch.setenv("LITELLM_MODELS", '["primary", "backup"]')
    monkeypatch.setenv("LITELLM_TEMPERATURE", "0.5")
    defaults = LiteLLMConfig.from_env()
    assert defaults.models == ("primary", "backup")
    assert defaults.temperature == 0.5
    explicit = LiteLLMConfig(temperature=0.1)
    assert explicit.temperature == 0.1
    override = defaults.with_overrides(models=("other",), temperature=None)
    assert override.models == ("other",)
    assert override.temperature is None
    assert defaults.models == ("primary", "backup")
    with pytest.raises(ValueError):
        defaults.with_overrides(typo=1)


def test_litellm_requires_configured_models(monkeypatch):
    monkeypatch.setenv("LITELLM_BASE_URL", "https://gateway.example/v1")
    monkeypatch.delenv("LITELLM_MODELS", raising=False)

    with pytest.raises(ValidationError):
        LiteLLMConfig.from_env()


@pytest.mark.parametrize(
    "changes",
    [
        {"models": ()},
        {"models": (" ",)},
        {"temperature": float("nan")},
        {"timeout_seconds": 0},
        {"timeout_seconds": float("inf")},
        {"max_tokens": -1},
        {"base_url": "https://user:secret@example.com"},
    ],
)
def test_invalid_configuration(changes):
    with pytest.raises(ValidationError):
        config().with_overrides(**changes)


@pytest.mark.asyncio
async def test_jev_typed_request_response():
    requests = []

    def handle(request):
        requests.append(request)
        return httpx.Response(
            200,
            json={
                "model": "jev-latest",
                "answers": {
                    "mounted": {"type": "noul", "noul": 0.98},
                },
            },
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as http:
        client = JevClient(http, config(JevConfig))
        result = await client.evaluate(
            JevRequest(
                state={"name": "Fixed rack"},
                questions={
                    "mounted": NoulQuestion(instructions="Is it mounted to the bike?")
                },
            )
        )
    assert result.answers["mounted"].noul == 0.98
    assert str(requests[0].url) == "https://llm.example/v1/systemone"
    body = json.loads(requests[0].content)
    assert body["state"] == {"name": "Fixed rack"}
    assert "temperature" not in body and "stream" not in body


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "answers",
    [
        {},
        {"mounted": {"type": "noul", "noul": 2}},
        {
            "mounted": {
                "type": "choice",
                "choice": "yes",
                "probabilities": {"yes": 1},
                "confidence": 1,
            }
        },
    ],
)
async def test_jev_rejects_invalid_answers(answers):
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(
            lambda _: httpx.Response(
                200, json={"model": "jev-latest", "answers": answers}
            ),
        )
    ) as http:
        with pytest.raises(LLMResponseError):
            await JevClient(http, config(JevConfig)).evaluate(
                JevRequest(
                    state="rack",
                    questions={"mounted": NoulQuestion(instructions="Mounted?")},
                )
            )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "status,body,expected_calls",
    [
        (404, {"error": {"code": "model_not_found"}}, 2),
        (422, {"detail": "invalid question"}, 1),
        (404, {"detail": "not found"}, 1),
        (401, {"error": {"code": "model_not_found"}}, 1),
        (429, {}, 1),
    ],
)
async def test_jev_conservative_fallback(status, body, expected_calls):
    calls = []

    def handle(request):
        calls.append(json.loads(request.content)["model"])
        return httpx.Response(status, json=body)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as http:
        with pytest.raises(ModelsNotFoundError if expected_calls == 2 else LLMError):
            await JevClient(http, config(JevConfig)).evaluate(
                JevRequest(
                    state="rack",
                    questions={"mounted": NoulQuestion(instructions="Mounted?")},
                )
            )
    assert calls == ["first", "second"][:expected_calls]


@pytest.mark.asyncio
@pytest.mark.parametrize("invalid", [False, True])
async def test_jev_choice_and_score(invalid):
    body = {
        "model": "jev-latest",
        "answers": {
            "category": {
                "type": "choice",
                "choice": "rack",
                "confidence": 0.9,
                "probabilities": {"rack": 0.9, "pump": 0.1},
            },
            "quality": {
                "type": "score",
                "score": 0.8 if not invalid else 2,
                "legend": {"0": "Low", "1": "High"},
                "confidence": 0.7,
                "probabilities": {"0": 0.2, "1": 0.8},
            },
        },
    }
    request = JevRequest(
        state="A fixed rack",
        questions={
            "category": ChoiceQuestion(
                instructions="Category?", criteria={"rack": None, "pump": None}
            ),
            "quality": ScoreQuestion(instructions="Quality?", criteria=["Low", "High"]),
        },
    )
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(
            lambda _: httpx.Response(200, json=body),
        )
    ) as http:
        client = JevClient(http, config(JevConfig))
        if invalid:
            with pytest.raises(LLMResponseError):
                await client.evaluate(request)
        else:
            result = await client.evaluate(request)
            assert result.answers["category"].choice == "rack"
            assert result.answers["quality"].score == 0.8


@pytest.mark.asyncio
async def test_concurrent_overrides_are_isolated():
    bodies = []

    async def handle(request):
        bodies.append(json.loads(request.content))
        await asyncio.sleep(0)
        return httpx.Response(200, json=response(with_tool_call=True))

    async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as http:
        client = LiteLLMClient(http, config())
        await asyncio.gather(
            client.generate(
                "one",
                config=client.config.with_overrides(models=("custom",), temperature=0),
            ),
            client.generate("two"),
        )
    assert bodies[0]["model"] == "custom"
    assert bodies[0]["temperature"] == 0
    assert bodies[1]["model"] == "first"
    assert "temperature" not in bodies[1]
    assert all("tools" not in body for body in bodies)
