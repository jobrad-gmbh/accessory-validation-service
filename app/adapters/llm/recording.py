import hashlib
import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from time import perf_counter
from typing import Any, Mapping, Protocol
from uuid import UUID, uuid4

from app.adapters.llm.client import LLMClient, LLMRequestSpec, LLMResponse
from app.adapters.llm.config import LLMClientConfig

logger = logging.getLogger(__name__)


@dataclass(frozen=True, kw_only=True)
class LLMRequest:
    """One attempted generation, associated with the product and validation that caused it."""

    product_id: UUID | None
    validation_id: str | None
    prompt: str
    instructions: str
    instructions_hash: str
    requested_models: tuple[str, ...]
    tools: tuple[Mapping[str, Any], ...]
    started_at: datetime
    duration_ms: int
    description: str | None = None
    response: LLMResponse | None = None
    error: str | None = None
    id: UUID = field(default_factory=uuid4)


class LLMRequestRepository(Protocol):
    async def save(self, request: LLMRequest) -> None: ...


class RecordingLLMClient:
    """Record every generation of the wrapped client, successful or failed."""

    def __init__(
        self, inner_llm_client: LLMClient, repository: LLMRequestRepository
    ) -> None:
        self.inner_llm_client = inner_llm_client
        self._repository = repository

    @property
    def config(self) -> LLMClientConfig:
        return self.inner_llm_client.config

    async def generate(self, request: LLMRequestSpec) -> LLMResponse:
        started_at = datetime.now(UTC)
        started = perf_counter()
        response: LLMResponse | None = None
        error: str | None = None
        try:
            response = await self.inner_llm_client.generate(request)
            return response
        except BaseException as exc:
            error = repr(exc)
            raise
        finally:
            await self._record(
                LLMRequest(
                    product_id=request.product_id,
                    validation_id=request.validation_id,
                    prompt=request.prompt,
                    instructions=request.instructions,
                    description=request.description,
                    instructions_hash=hashlib.sha256(
                        request.instructions.encode("utf-8")
                    ).hexdigest(),
                    requested_models=(
                        request.config or self.inner_llm_client.config
                    ).models,
                    tools=tuple(request.tools),
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
