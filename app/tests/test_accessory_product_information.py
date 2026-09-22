import json
from typing import Any, Mapping, Sequence

import pytest
from pydantic import HttpUrl

from app.adapters.llm import (
    ChatConfig,
    LLMResponse,
    LLMSource,
    LiteLLMConfig,
    UnsupportedLLMToolError,
)
from app.domain.errors import (
    ProductInformationRetrievalError,
    WebSearchNotSupportedError,
)
from app.domain.product import ProductInput, ProductType
from app.domain.validations.accessories import AccessoryProductInformationService


class FakeLLMClient:
    def __init__(
        self,
        response: LLMResponse | None = None,
        error: Exception | None = None,
    ) -> None:
        self.config = LiteLLMConfig(
            base_url=HttpUrl("https://llm.example/v1"), models=("selected-model",)
        )
        self.response = response
        self.error = error
        self.calls: list[dict[str, object]] = []

    async def generate(
        self,
        prompt: str,
        *,
        instructions: str = "",
        config: ChatConfig | None = None,
        tools: Sequence[Mapping[str, Any]] = (),
        tool_choice: str | Mapping[str, Any] | None = None,
    ) -> LLMResponse:
        self.calls.append(
            {
                "prompt": prompt,
                "instructions": instructions,
                "config": config,
                "tools": tools,
                "tool_choice": tool_choice,
            }
        )
        if self.error is not None:
            raise self.error
        assert self.response is not None
        return self.response


def product() -> ProductInput:
    return ProductInput(
        product_type=ProductType.ACCESSORY,
        brand="Ortlieb",
        model="Quick Rack",
        category="rear rack",
        year=2025,
    )


@pytest.mark.asyncio
async def test_retrieves_condensed_information_with_required_web_search():
    source = LLMSource("https://manufacturer.example/rack", "Quick Rack")
    client = FakeLLMClient(
        LLMResponse(
            "A removable rear bicycle rack.",
            "selected-model",
            "completed",
            ("web_search_call",),
            (source,),
        )
    )

    result = await AccessoryProductInformationService(client).retrieve(product())

    assert result.summary == "A removable rear bicycle rack."
    assert result.used_web_search is True
    assert result.sources == (source,)
    call = client.calls[0]
    assert call["tools"] == (
        {
            "type": "web_search",
            "parameters": {"engine": "auto", "max_results": 5},
        },
    )
    assert call["tool_choice"] == "required"
    assert json.loads(str(call["prompt"])) == {
        "brand": "Ortlieb",
        "model": "Quick Rack",
        "category": "rear rack",
        "year": 2025,
        "size": None,
        "color": None,
    }
    assert "Do not make a leasing decision" in str(call["instructions"])


@pytest.mark.asyncio
async def test_search_can_be_disabled_for_models_without_that_capability():
    client = FakeLLMClient(
        LLMResponse("Known product information.", "local-model", "completed")
    )

    result = await AccessoryProductInformationService(client).retrieve(
        product(), use_web_search=False
    )

    assert result.used_web_search is False
    assert client.calls[0]["tools"] == ()
    assert client.calls[0]["tool_choice"] is None


@pytest.mark.asyncio
async def test_unsupported_search_model_has_actionable_domain_error():
    client = FakeLLMClient(
        error=UnsupportedLLMToolError("web_search", "local-model", status_code=400)
    )

    with pytest.raises(WebSearchNotSupportedError) as error:
        await AccessoryProductInformationService(client).retrieve(product())

    assert error.value.model == "local-model"
    assert "Choose a web-search-capable model or disable web search" in str(
        error.value
    )


@pytest.mark.asyncio
async def test_required_search_cannot_silently_return_unsearched_information():
    client = FakeLLMClient(
        LLMResponse("Unsearched information.", "selected-model", "completed")
    )

    with pytest.raises(ProductInformationRetrievalError, match="without performing"):
        await AccessoryProductInformationService(client).retrieve(product())
