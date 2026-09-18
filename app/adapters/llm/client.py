from dataclasses import dataclass
from typing import Protocol

from app.adapters.llm.config import ChatConfig


@dataclass(frozen=True)
class LLMResponse:
    text: str
    model: str
    finish_reason: str


class LLMClient(Protocol):
    @property
    def config(self) -> ChatConfig: ...

    async def generate(
        self,
        prompt: str,
        *,
        instructions: str = "",
        config: ChatConfig | None = None,
    ) -> LLMResponse: ...
