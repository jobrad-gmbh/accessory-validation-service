from dataclasses import dataclass
from typing import Any, Mapping, Protocol, Sequence
from uuid import UUID

from app.adapters.llm.config import LLMClientConfig


@dataclass(frozen=True)
class LLMSource:
    url: str
    title: str | None = None


@dataclass(frozen=True)
class LLMUsage:
    input_tokens: int | None = None
    output_tokens: int | None = None
    total_tokens: int | None = None


@dataclass(frozen=True)
class LLMResponse:
    text: str
    model: str
    status: str
    tool_calls: tuple[str, ...] = ()
    sources: tuple[LLMSource, ...] = ()
    usage: LLMUsage | None = None


@dataclass(frozen=True, kw_only=True)
class LLMRequestSpec:
    prompt: str
    instructions: str = ""
    config: LLMClientConfig | None = None
    tools: Sequence[Mapping[str, Any]] = ()
    tool_choice: str | Mapping[str, Any] | None = None
    # Metadata for observability only; never sent to the model.
    description: str | None = None
    product_id: UUID | None = None
    validation_id: str | None = None


class LLMClient(Protocol):
    @property
    def config(self) -> LLMClientConfig: ...

    async def generate(self, request: LLMRequestSpec) -> LLMResponse: ...
