"""Async PostgreSQL implementations of the persistence contracts."""

from sqlalchemy import insert
from sqlalchemy.ext.asyncio import AsyncEngine

from app.adapters.persistence.postgresql.tables import (
    llm_requests,
    products,
    validation_executions,
)
from app.adapters.llm.recording import LLMRequest
from app.domain.validation_results import ValidationReport


class PostgresValidationReportRepository:
    def __init__(self, engine: AsyncEngine) -> None:
        self._engine = engine

    async def save(self, report: ValidationReport) -> None:
        product = report.product
        # An all-or-nothing transaction prevents partial reports, or products stored without validation result.
        async with self._engine.begin() as connection:
            await connection.execute(
                insert(products).values(
                    id=product.id,
                    created_at=product.created_at,
                    source=product.origin.source,
                    external_ref=product.origin.external_ref,
                    product_type=product.product_type.value,
                    brand=product.brand,
                    model=product.model,
                    year=product.year,
                    size=product.size,
                    color=product.color,
                    price=product.price,
                    category=product.category,
                    report_status=report.status.value,
                )
            )
            for position, execution in enumerate(report.validations):
                await connection.execute(
                    insert(validation_executions).values(
                        id=execution.id,
                        product_id=product.id,
                        position=position,
                        validation_id=execution.validation_id,
                        executed_at=execution.executed_at,
                        status=execution.result.status.value,
                        details=execution.result.details,
                    )
                )


class PostgresLLMRequestRepository:
    def __init__(self, engine: AsyncEngine) -> None:
        self._engine = engine

    async def save(self, request: LLMRequest) -> None:
        response = request.response
        async with self._engine.begin() as connection:
            await connection.execute(
                insert(llm_requests).values(
                    id=request.id,
                    validation_execution_id=request.validation_execution_id,
                    prompt=request.prompt,
                    instructions=request.instructions,
                    instructions_hash=request.instructions_hash,
                    requested_models=list(request.requested_models),
                    tools=[dict(tool) for tool in request.tools],
                    started_at=request.started_at,
                    response=(
                        {
                            "text": response.text,
                            "model": response.model,
                            "status": response.status,
                            "tool_calls": list(response.tool_calls),
                            "sources": [
                                {"url": source.url, "title": source.title}
                                for source in response.sources
                            ],
                        }
                        if response is not None
                        else None
                    ),
                    error=request.error,
                )
            )
