import hashlib
import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from time import perf_counter
from typing import Any, Mapping, Protocol, Sequence
from uuid import UUID, uuid4

from app.adapters.llm.client import LLMClient, LLMResponse
from app.adapters.llm.config import ChatConfig
from app.domain.execution_context import current_validation_execution_id

logger = logging.getLogger(__name__)


@dataclass(frozen=True, kw_only=True)
class LLMRequest:
    """One attempted generation, associated with the validation that caused it."""

    validation_execution_id: UUID | None
    prompt: str
    instructions: str
    instructions_hash: str
    requested_models: tuple[str, ...]
    tools: tuple[Mapping[str, Any], ...]
    started_at: datetime
    duration_ms: int
    response: LLMResponse | None = None
    error: str | None = None
    id: UUID = field(default_factory=uuid4)


class LLMRequestRepository(Protocol):
    async def save(self, request: LLMRequest) -> None: ...


class RecordingLLMClient:
    """Record every generation of the wrapped client, successful or failed.

    A failing sink is logged and never changes the outcome of the generation.
    """

    def __init__(
        self, inner_llm_client: LLMClient, repository: LLMRequestRepository
    ) -> None:
        self.inner_llm_client = inner_llm_client
        self._repository = repository

    @property
    def config(self) -> ChatConfig:
        return self.inner_llm_client.config

    async def generate(
        self,
        prompt: str,
        *,
        instructions: str = "",
        config: ChatConfig | None = None,
        tools: Sequence[Mapping[str, Any]] = (),
        tool_choice: str | Mapping[str, Any] | None = None,
    ) -> LLMResponse:
        started_at = datetime.now(UTC)
        started = perf_counter()
        response: LLMResponse | None = None
        error: str | None = None
        try:
            response = await self.inner_llm_client.generate(
                prompt,
                instructions=instructions,
                config=config,
                tools=tools,
                tool_choice=tool_choice,
            )
            return response
        except BaseException as exc:
            error = repr(exc)
            raise
        finally:
            await self._record(
                LLMRequest(
                    validation_execution_id=current_validation_execution_id(),
                    prompt=prompt,
                    instructions=instructions,
                    instructions_hash=hashlib.sha256(
                        instructions.encode("utf-8")
                    ).hexdigest(),
                    requested_models=(config or self.inner_llm_client.config).models,
                    tools=tuple(tools),
                    started_at=started_at,
                    duration_ms=round((perf_counter() - started) * 1000),
                    response=response,
                    error=error,
                )
            )

    async def _record(self, request: LLMRequest) -> None:
        try:
            await self._repository.save(request)
        except Exception:
            logger.exception("Could not record LLM request %s", request.id)
