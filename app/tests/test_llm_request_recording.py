import asyncio
from unittest.mock import AsyncMock

import pytest

from app.adapters.llm import (
    LiteLLMConfig,
    LLMRequestSpec,
    LLMResponse,
    RecordingLLMClient,
)
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
        await self._llm_client.generate(
            LLMRequestSpec(
                prompt="first",
                instructions="Be brief",
                description="first_check",
                product_id=request.product.id,
                validation_id=self.id,
            )
        )
        await self._llm_client.generate(
            LLMRequestSpec(
                prompt="second", product_id=request.product.id, validation_id=self.id
            )
        )
        return ValidationResult(status=ValidationStatus.PASSED, details="Passed.")


def recorded_client(**generate):
    requests = []
    repository = AsyncMock()
    repository.save.side_effect = lambda request: requests.append(request)
    client = RecordingLLMClient(inner_client(**generate), repository)
    return client, requests


def test_requests_are_associated_with_the_product_and_validation():
    client, requests = recorded_client(return_value=RESPONSE)
    submitted = request()

    asyncio.run(MakesTwoLLMRequests(client).validate(submitted))

    assert [request.prompt for request in requests] == ["first", "second"]
    assert all(request.product_id == submitted.product.id for request in requests)
    assert all(request.validation_id == "makes_two_llm_requests" for request in requests)
    assert requests[0].response is RESPONSE
    assert requests[0].instructions == "Be brief"
    assert [request.description for request in requests] == ["first_check", None]
    forwarded = client.inner_llm_client.generate.await_args_list[0].args[0]
    assert forwarded.prompt == "first"
    assert forwarded.instructions == "Be brief"
    assert requests[0].requested_models == ("default-model",)
    assert requests[0].instructions_hash != requests[1].instructions_hash


def test_requests_outside_a_validation_have_no_identity():
    client, requests = recorded_client(return_value=RESPONSE)

    assert asyncio.run(client.generate(LLMRequestSpec(prompt="hello"))) is RESPONSE
    assert requests[0].product_id is None
    assert requests[0].validation_id is None


def test_failed_requests_are_recorded_and_reraised():
    failure = RuntimeError("Provider unavailable")
    client, requests = recorded_client(side_effect=failure)

    with pytest.raises(RuntimeError, match="Provider unavailable"):
        asyncio.run(
            client.generate(LLMRequestSpec(prompt="hello", description="failed_check"))
        )

    assert requests[0].response is None
    assert requests[0].description == "failed_check"
    assert "Provider unavailable" in requests[0].error


def test_storage_failure_does_not_change_generation_result():
    repository = AsyncMock()
    repository.save.side_effect = RuntimeError("Database unavailable")
    client = RecordingLLMClient(inner_client(return_value=RESPONSE), repository)

    assert asyncio.run(client.generate(LLMRequestSpec(prompt="hello"))) is RESPONSE
    repository.save.assert_awaited_once()
