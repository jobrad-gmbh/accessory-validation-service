from dataclasses import dataclass
from typing import Any, Mapping, Protocol, Sequence

from app.adapters.llm.config import ChatConfig


@dataclass(frozen=True)
class LLMResponse:
    text: str
    model: str
    status: str


class LLMClient(Protocol):
    @property
    def config(self) -> ChatConfig: ...

    async def generate(
        self,
        prompt: str,
        *,
        instructions: str = "",
        config: ChatConfig | None = None,
        tools: Sequence[Mapping[str, Any]] = (),
    ) -> LLMResponse: ...
