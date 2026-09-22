import json
from dataclasses import dataclass
from pathlib import Path

from app.adapters.llm import (
    ChatConfig,
    LLMClient,
    LLMSource,
    UnsupportedLLMToolError,
)
from app.domain.errors import (
    ProductInformationRetrievalError,
    WebSearchNotSupportedError,
)
from app.domain.product import ProductInput

PROMPT_PATH = Path(__file__).with_name("prompts") / "product_information.md"
WEB_SEARCH_TOOL = {
    "type": "web_search",
    "parameters": {"engine": "auto", "max_results": 5},
}


@dataclass(frozen=True)
class AccessoryProductInformation:
    summary: str
    model: str
    used_web_search: bool
    sources: tuple[LLMSource, ...] = ()


class AccessoryProductInformationService:
    """Retrieve and condense accessory facts without acting as a criterion."""

    def __init__(self, llm_client: LLMClient) -> None:
        self._llm_client = llm_client

    async def retrieve(
        self,
        product: ProductInput,
        *,
        use_web_search: bool = True,
        config: ChatConfig | None = None,
    ) -> AccessoryProductInformation:
        tools = (WEB_SEARCH_TOOL,) if use_web_search else ()
        tool_choice = "required" if use_web_search else None
        try:
            response = await self._llm_client.generate(
                _product_prompt(product),
                instructions=PROMPT_PATH.read_text(encoding="utf-8").strip(),
                config=config,
                tools=tools,
                tool_choice=tool_choice,
            )
        except UnsupportedLLMToolError as error:
            raise WebSearchNotSupportedError(error.model) from None

        used_web_search = "web_search_call" in response.tool_calls
        if use_web_search and not used_web_search:
            raise ProductInformationRetrievalError(
                f"Model '{response.model}' returned product information without "
                "performing the required web search."
            )
        return AccessoryProductInformation(
            summary=response.text.strip(),
            model=response.model,
            used_web_search=used_web_search,
            sources=response.sources,
        )


def _product_prompt(product: ProductInput) -> str:
    return json.dumps(
        {
            "brand": product.brand,
            "model": product.model,
            "category": product.category,
            "year": product.year,
            "size": product.size,
            "color": product.color,
        },
        ensure_ascii=False,
    )
