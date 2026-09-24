import asyncio
from contextlib import asynccontextmanager
from decimal import Decimal
from typing import Any, cast

import pytest
from sqlalchemy.dialects import postgresql
from sqlalchemy.ext.asyncio import AsyncEngine

from app.adapters.persistence.postgresql import PostgresLLMRequestRepository, PostgresValidationReportRepository
from app.adapters.llm.client import LLMResponse, LLMSource
from app.adapters.llm.recording import LLMRequest
from app.domain.criterion import CriterionAnswer, CriterionResult, SpecialRuleResult
from app.domain.product import Product, ProductOrigin, ProductType
from app.domain.validation_results import (
    ReportStatus,
    ValidationExecution,
    ValidationReport,
    ValidationResult,
    ValidationStatus,
)
from datetime import UTC, datetime


class RecordingConnection:
    def __init__(self, fail_after: int | None = None) -> None:
        self.statements: list[tuple[str, Any]] = []
        self.fail_after = fail_after

    async def execute(self, statement: Any, parameters: Any = None) -> None:
        if self.fail_after is not None and len(self.statements) == self.fail_after:
            raise RuntimeError("Database unavailable")
        compiled = statement.compile(dialect=postgresql.dialect())
        self.statements.append((statement.table.name, parameters or compiled.params))


class RecordingEngine:
    def __init__(self, fail_after: int | None = None) -> None:
        self.connection = RecordingConnection(fail_after)
        self.committed = False
        self.rolled_back = False

    @asynccontextmanager
    async def begin(self):
        try:
            yield self.connection
        except BaseException:
            self.rolled_back = True
            raise
        else:
            self.committed = True


def report() -> ValidationReport:
    product = Product(
        product_type=ProductType.ACCESSORY,
        brand="Example",
        model="Rack",
        price=Decimal("49.99"),
        origin=ProductOrigin(source="odoo", external_ref="ACC-42"),
    )
    execution = ValidationExecution(
        product=product,
        validation_id="accessory_leasability",
        result=ValidationResult(
            status=ValidationStatus.REJECTED,
            details="Not leasable.",
            criterion_results=(
                CriterionResult(CriterionAnswer.YES, "Fixed.", "mounted"),
                SpecialRuleResult(
                    CriterionAnswer.YES, CriterionAnswer.NO, "Override.", "special_rules"
                ),
            ),
        ),
    )
    return ValidationReport(
        product=product, status=ReportStatus.INVALID, validations=(execution,)
    )


def test_report_save_writes_complete_history_in_one_transaction():
    engine = RecordingEngine()
    saved = report()

    asyncio.run(PostgresValidationReportRepository(cast(AsyncEngine, engine)).save(saved))

    assert engine.committed
    assert [table for table, _ in engine.connection.statements] == [
        "products", "validation_executions"
    ]
    product_row = engine.connection.statements[0][1]
    execution_row = engine.connection.statements[1][1]
    assert product_row["id"] == saved.product.id
    assert product_row["price"] == Decimal("49.99")
    assert product_row["report_status"] == "INVALID"
    assert execution_row["product_id"] == saved.product.id
    assert execution_row["status"] == "REJECTED"


def test_report_save_rolls_back_after_a_child_write_fails():
    engine = RecordingEngine(fail_after=1)

    with pytest.raises(RuntimeError, match="Database unavailable"):
        asyncio.run(PostgresValidationReportRepository(cast(AsyncEngine, engine)).save(report()))

    assert engine.rolled_back
    assert not engine.committed


def test_llm_request_save_keeps_response_and_validation_identity():
    engine = RecordingEngine()
    execution = report().validations[0]
    request = LLMRequest(
        validation_execution_id=execution.id,
        prompt="Is this leasable?",
        instructions="Answer briefly",
        instructions_hash="a" * 64,
        requested_models=("first", "second"),
        tools=({"type": "web_search"},),
        started_at=datetime.now(UTC),
        duration_ms=123,
        response=LLMResponse(
            text="Yes",
            model="second",
            status="completed",
            tool_calls=("search",),
            sources=(LLMSource(url="https://example.com", title="Source"),),
        ),
    )

    asyncio.run(PostgresLLMRequestRepository(cast(AsyncEngine, engine)).save(request))

    assert engine.committed
    table, row = engine.connection.statements[0]
    assert table == "llm_requests"
    assert row["validation_execution_id"] == execution.id
    assert row["requested_models"] == ["first", "second"]
    assert row["response"]["sources"] == [
        {"url": "https://example.com", "title": "Source"}
    ]
