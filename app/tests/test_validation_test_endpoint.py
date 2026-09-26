import json
from unittest.mock import AsyncMock

import httpx
import pytest
from fastapi.testclient import TestClient

from app.adapters.llm import LiteLLMClient, LiteLLMConfig, RecordingLLMClient
from app.main import app

SERVER_KEY = "server-secret-key"
CALLER_KEY = "caller-key"

PAYLOAD = {
    "brand": "Example",
    "model": "Rack",
    "price": "49.99",
    "origin": {"source": "odoo", "external_ref": "ACC-42"},
}


def llm_response(text, *, with_web_search=False):
    output = []
    if with_web_search:
        output.append({"type": "web_search_call", "id": "ws", "status": "completed"})
    output.append(
        {
            "type": "message",
            "role": "assistant",
            "content": [{"type": "output_text", "text": text, "annotations": []}],
        }
    )
    return {"object": "response", "status": "completed", "model": "m", "output": output}


@pytest.fixture
def api():
    """App state wired like production, but without a database or real LLM."""
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        body = json.loads(request.content)
        instructions = body.get("instructions", "")
        if body.get("tools"):
            text = "A rear rack."
        elif "category-specific bicycle-leasing rules" in instructions:
            text = '{"answer": "NO", "leasable": "UNKNOWN", "details": "None."}'
        elif "Decide whether the submitted product clearly matches" in instructions:
            text = '{"answer": "NO", "details": "Not excluded."}'
        else:
            text = '{"answer": "YES", "details": "Leasable."}'
        return httpx.Response(
            200, json=llm_response(text, with_web_search=bool(body.get("tools")))
        )

    http_client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    server_config = LiteLLMConfig(
        base_url="https://server-gateway.example/v1",
        api_key=SERVER_KEY,
        models=("server-model",),
        temperature=0.7,
    )
    report_repository = AsyncMock()
    llm_request_repository = AsyncMock()
    app.state.http_client = http_client
    app.state.validation_report_repository = report_repository
    app.state.litellm_client = RecordingLLMClient(
        LiteLLMClient(http_client, server_config), llm_request_repository
    )
    # No lifespan: the fixture provides the state that startup would create.
    client = TestClient(app)
    yield client, requests, report_repository, llm_request_repository


def post(client, **extra):
    return client.post("/api/v1/accessories/validate/test", json={**PAYLOAD, **extra})


def test_requires_api_key(api):
    client, requests, *_ = api

    assert post(client).status_code == 422
    assert post(client, llm_settings={}).status_code == 422
    assert post(client, llm_settings={"api_key": ""}).status_code == 422
    assert requests == []


def test_never_uses_server_api_key_and_stores_nothing(api):
    client, requests, report_repository, llm_request_repository = api

    response = post(client, llm_settings={"api_key": CALLER_KEY})

    assert response.status_code == 200, response.text
    assert response.json()["status"] == "VALID"
    assert requests
    for sent in requests:
        assert sent.headers["Authorization"] == f"Bearer {CALLER_KEY}"
        assert SERVER_KEY not in sent.headers["Authorization"]
        assert sent.url.host == "server-gateway.example"
    report_repository.save.assert_not_awaited()
    llm_request_repository.save.assert_not_awaited()


def test_general_settings_override_server_defaults(api):
    client, requests, *_ = api

    response = post(
        client,
        llm_settings={
            "api_key": CALLER_KEY,
            "base_url": "https://caller-gateway.example/v1",
            "models": ["caller-model"],
            "temperature": 0.1,
            "max_tokens": 300,
            "reasoning_effort": "low",
        },
    )

    assert response.status_code == 200, response.text
    information_request = json.loads(requests[0].content)
    assert requests[0].url == "https://caller-gateway.example/v1/responses"
    assert information_request["model"] == "caller-model"
    assert information_request["temperature"] == 0.1
    assert information_request["max_output_tokens"] == 300
    assert information_request["reasoning"] == {"effort": "low"}
    # Criteria keep their default models, but inherit the other general settings.
    criterion_request = json.loads(requests[1].content)
    assert criterion_request["model"] == "glm-5.3"
    assert criterion_request["temperature"] == 0.1
    assert criterion_request["reasoning"] == {"effort": "low"}


def test_criterion_settings_apply_only_to_their_criterion(api):
    client, requests, *_ = api

    response = post(
        client,
        llm_settings={"api_key": CALLER_KEY, "temperature": 0.3},
        criterion_settings={
            "explicitly_leasable_type": {"models": ["special"], "temperature": 0}
        },
    )

    assert response.status_code == 200, response.text
    not_leasable, leasable = (json.loads(r.content) for r in requests[1:3])
    assert not_leasable["model"] == "glm-5.3"
    assert not_leasable["temperature"] == 0.3
    assert leasable["model"] == "special"
    assert leasable["temperature"] == 0
    for sent in requests:
        assert sent.headers["Authorization"] == f"Bearer {CALLER_KEY}"


@pytest.mark.parametrize(
    "criterion_settings",
    [
        {"unknown_criterion": {}},
        {"special_rules": {"api_key": "other"}},
        {"special_rules": {"base_url": "https://other.example/v1"}},
        {"special_rules": {"models": []}},
        {"special_rules": {"temperature": 3}},
        {"special_rules": {"reasoning_effort": "extreme"}},
    ],
)
def test_rejects_invalid_criterion_settings(api, criterion_settings):
    client, requests, *_ = api

    response = post(
        client,
        llm_settings={"api_key": CALLER_KEY},
        criterion_settings=criterion_settings,
    )

    assert response.status_code == 422
    assert requests == []


def test_api_key_is_not_echoed_in_validation_errors(api):
    client, *_ = api

    response = post(
        client, llm_settings={"api_key": CALLER_KEY, "temperature": "hot"}
    )

    assert response.status_code == 422
    assert CALLER_KEY not in response.text
