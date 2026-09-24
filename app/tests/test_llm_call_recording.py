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


class CallsLLMTwice(Validation):
    id = "calls_llm_twice"

    def __init__(self, llm_client):
        self._llm_client = llm_client

    async def evaluate_result(self, request):
        await self._llm_client.generate("first", instructions="Be brief")
        await self._llm_client.generate("second")
        return ValidationResult(status=ValidationStatus.PASSED, details="Passed.")


def recorded_client(**generate):
    calls = []
    client = RecordingLLMClient(inner_client(**generate))

    async def record(call):
        calls.append(call)

    client._record = record
    return client, calls


def test_calls_are_associated_with_the_validation_execution():
    client, calls = recorded_client(return_value=RESPONSE)

    execution = asyncio.run(CallsLLMTwice(client).validate(request()))

    assert [call.prompt for call in calls] == ["first", "second"]
    assert all(call.validation_execution_id == execution.id for call in calls)
    assert calls[0].response is RESPONSE
    assert calls[0].instructions == "Be brief"
    assert calls[0].requested_models == ("default-model",)
    assert calls[0].instructions_hash != calls[1].instructions_hash
    assert current_validation_execution_id() is None


def test_calls_outside_a_validation_have_no_execution_id():
    client, calls = recorded_client(return_value=RESPONSE)

    assert asyncio.run(client.generate("hello")) is RESPONSE
    assert calls[0].validation_execution_id is None


def test_failed_calls_are_recorded_and_reraised():
    failure = RuntimeError("Provider unavailable")
    client, calls = recorded_client(side_effect=failure)

    with pytest.raises(RuntimeError, match="Provider unavailable"):
        asyncio.run(client.generate("hello"))

    assert calls[0].response is None
    assert "Provider unavailable" in calls[0].error


def test_concurrent_validations_keep_their_own_execution_id():
    client, calls = recorded_client(return_value=RESPONSE)

    async def run_both():
        return await asyncio.gather(
            CallsLLMTwice(client).validate(request()),
            CallsLLMTwice(client).validate(request()),
        )

    first, second = asyncio.run(run_both())

    ids = [call.validation_execution_id for call in calls]
    assert ids.count(first.id) == 2
    assert ids.count(second.id) == 2
