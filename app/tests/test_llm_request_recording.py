import asyncio
from unittest.mock import AsyncMock

import pytest

from app.adapters.llm import (
    LiteLLMConfig,
    LLMResponse,
    RecordingLLMClient,
)
from app.domain.execution_context import current_validation_execution_id
from app.domain.product import Product, ProductOrigin, ProductType
from app.domain.validation import Validation, ValidationRequest
from app.domain.validation_results import ValidationResult, ValidationStatus

RESPONSE = LLMResponse(text='{"ok": true}', model="actual-model", status="completed")


def inner_client(**generate):
    client = AsyncMock()
    client.config = LiteLLMConfig(
        base_url="https://gateway.example/v1", models=("default-model",)
    )
    client.generate = AsyncMock(**generate)
    return client


def request():
    return ValidationRequest(
        product=Product(
            product_type=ProductType.ACCESSORY,
            brand="Example",
            model="Rack",
            origin=ProductOrigin(source="odoo", external_ref="ACC-42"),
        )
    )


class MakesTwoLLMRequests(Validation):
    id = "makes_two_llm_requests"

    def __init__(self, llm_client):
        self._llm_client = llm_client

    async def evaluate_result(self, request):
        await self._llm_client.generate("first", instructions="Be brief")
        await self._llm_client.generate("second")
        return ValidationResult(status=ValidationStatus.PASSED, details="Passed.")


def recorded_client(**generate):
    requests = []
    repository = AsyncMock()
    repository.save.side_effect = lambda request: requests.append(request)
    client = RecordingLLMClient(inner_client(**generate), repository)
    return client, requests


def test_requests_are_associated_with_the_validation_execution():
    client, requests = recorded_client(return_value=RESPONSE)

    execution = asyncio.run(MakesTwoLLMRequests(client).validate(request()))

    assert [request.prompt for request in requests] == ["first", "second"]
    assert all(request.validation_execution_id == execution.id for request in requests)
    assert requests[0].response is RESPONSE
    assert requests[0].instructions == "Be brief"
    assert requests[0].requested_models == ("default-model",)
    assert requests[0].instructions_hash != requests[1].instructions_hash
    assert current_validation_execution_id() is None


def test_requests_outside_a_validation_have_no_execution_id():
    client, requests = recorded_client(return_value=RESPONSE)

    assert asyncio.run(client.generate("hello")) is RESPONSE
    assert requests[0].validation_execution_id is None


def test_failed_requests_are_recorded_and_reraised():
    failure = RuntimeError("Provider unavailable")
    client, requests = recorded_client(side_effect=failure)

    with pytest.raises(RuntimeError, match="Provider unavailable"):
        asyncio.run(client.generate("hello"))

    assert requests[0].response is None
    assert "Provider unavailable" in requests[0].error


def test_storage_failure_does_not_change_generation_result():
    repository = AsyncMock()
    repository.save.side_effect = RuntimeError("Database unavailable")
    client = RecordingLLMClient(inner_client(return_value=RESPONSE), repository)

    assert asyncio.run(client.generate("hello")) is RESPONSE
    repository.save.assert_awaited_once()


def test_concurrent_validations_keep_their_own_execution_id():
    client, requests = recorded_client(return_value=RESPONSE)

    async def run_both():
        return await asyncio.gather(
            MakesTwoLLMRequests(client).validate(request()),
            MakesTwoLLMRequests(client).validate(request()),
        )

    first, second = asyncio.run(run_both())

    ids = [request.validation_execution_id for request in requests]
    assert ids.count(first.id) == 2
    assert ids.count(second.id) == 2
