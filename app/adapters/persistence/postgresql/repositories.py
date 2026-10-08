"""Async PostgreSQL implementations of the persistence contracts."""

from sqlalchemy import insert
from sqlalchemy.ext.asyncio import AsyncEngine

from app.adapters.persistence.postgresql.tables import (
    llm_request,
    product,
    validation_execution,
)
from app.adapters.llm.recording import LLMRequest
from app.domain.validation_results import ValidationReport


class PostgresValidationReportRepository:
    def __init__(self, engine: AsyncEngine) -> None:
        self._engine = engine

    async def save(self, report: ValidationReport) -> None:
        submitted_product = report.product
        leasability_status = next(
            (
                execution.result.status
                for execution in report.validations
                if execution.validation_id == "accessory_leasability"
            ),
            None,
        )
        # An all-or-nothing transaction prevents partial reports, or products stored without validation result.
        async with self._engine.begin() as connection:
            await connection.execute(
                insert(product).values(
                    id=submitted_product.id,
                    created_at=submitted_product.created_at,
                    source=submitted_product.origin.source,
                    external_ref=submitted_product.origin.external_ref,
                    product_type=submitted_product.product_type.value,
                    brand=submitted_product.brand,
                    model=submitted_product.model,
                    year=submitted_product.year,
                    size=submitted_product.size,
                    color=submitted_product.color,
                    price=submitted_product.price,
                    category=submitted_product.category,
                    validation_status=report.status.value,
                    leasability_validation_status=(
                        leasability_status.value if leasability_status is not None else None
                    ),
                )
            )
            for position, execution in enumerate(report.validations):
                await connection.execute(
                    insert(validation_execution).values(
                        id=execution.id,
                        product_id=submitted_product.id,
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
        usage = response.usage if response is not None else None
        async with self._engine.begin() as connection:
            await connection.execute(
                insert(llm_request).values(
                    id=request.id,
                    product_id=request.product_id,
                    validation_id=request.validation_id,
                    description=request.description,
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
                    input_tokens=usage.input_tokens if usage is not None else None,
                    output_tokens=usage.output_tokens if usage is not None else None,
                    total_tokens=usage.total_tokens if usage is not None else None,
                    error=request.error,
                )
            )
