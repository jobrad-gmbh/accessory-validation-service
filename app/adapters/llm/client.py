from dataclasses import dataclass
from typing import Any, Mapping, Protocol, Sequence

from app.adapters.llm.config import LLMClientConfig


@dataclass(frozen=True)
class LLMSource:
    url: str
    title: str | None = None


@dataclass(frozen=True)
class LLMResponse:
    text: str
    model: str
    status: str
    tool_calls: tuple[str, ...] = ()
    sources: tuple[LLMSource, ...] = ()


class LLMClient(Protocol):
    @property
    def config(self) -> LLMClientConfig: ...

    async def generate(
        self,
        prompt: str,
        *,
        instructions: str = "",
        config: LLMClientConfig | None = None,
        tools: Sequence[Mapping[str, Any]] = (),
        tool_choice: str | Mapping[str, Any] | None = None,
    ) -> LLMResponse: ...
