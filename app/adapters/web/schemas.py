from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.domain.product import (
    Product,
    ProductContext,
    ProductOrigin,
    ProductType,
)
from app.domain.validation import (
    ValidationRequest,
)
from app.domain.criterion import CriterionAnswer, CriterionResult, SpecialRuleResult
from app.domain.validation_results import (
    ReportStatus,
    ValidationReport,
    ValidationStatus,
)


class AccessoryOrigin(BaseModel):
    """Reference to the accessory record in its origin system."""

    model_config = ConfigDict(str_strip_whitespace=True)

    external_ref: str = Field(min_length=1)
    source: str = Field(min_length=1)


class AccessoryInput(BaseModel):
    """Complete submitted payload, including validation context and origin."""

    model_config = ConfigDict(str_strip_whitespace=True)

    brand: str = Field(min_length=1)
    model: str = Field(min_length=1)
    price: Decimal = Field(ge=0, allow_inf_nan=False)
    context: ProductContext = Field(default_factory=ProductContext)
    origin: AccessoryOrigin
    year: int | None = None
    category: str | None = None
    color: str | None = None
    size: str | None = None

    def to_domain(self) -> ValidationRequest:
        return ValidationRequest(
            product=Product(
                product_type=ProductType.ACCESSORY,
                brand=self.brand,
                model=self.model,
                price=self.price,
                year=self.year,
                category=self.category,
                color=self.color,
                size=self.size,
                origin=ProductOrigin(
                    source=self.origin.source,
                    external_ref=self.origin.external_ref,
                ),
            ),
            context=self.context,
        )


class CriterionResultResponse(BaseModel):
    """One evaluated criterion that explains a validation result."""

    criterion_id: str
    answer: CriterionAnswer
    details: str


class SpecialRuleResultResponse(CriterionResultResponse):
    leasable: CriterionAnswer


def _criterion_response(
    result: CriterionResult | SpecialRuleResult,
) -> CriterionResultResponse:
    if isinstance(result, SpecialRuleResult):
        return SpecialRuleResultResponse(
            criterion_id=result.criterion_id,
            answer=result.answer,
            details=result.details,
            leasable=result.leasable,
        )
    return CriterionResultResponse(
        criterion_id=result.criterion_id,
        answer=result.answer,
        details=result.details,
    )


class ValidationResponse(BaseModel):
    """Public result of one validation execution."""

    id: UUID
    validation_id: str
    status: ValidationStatus
    details: str
    criterion_results: list[SpecialRuleResultResponse | CriterionResultResponse]
    executed_at: datetime


class ValidationReportResponse(BaseModel):
    """HTTP representation of the domain validation report."""

    product_id: UUID
    status: ReportStatus
    validations: list[ValidationResponse]

    @classmethod
    def from_domain(cls, report: ValidationReport) -> "ValidationReportResponse":
        return cls(
            product_id=report.product.id,
            status=report.status,
            validations=[
                ValidationResponse(
                    id=execution.id,
                    validation_id=execution.validation_id,
                    status=execution.result.status,
                    details=execution.result.details,
                    criterion_results=[
                        _criterion_response(result)
                        for result in execution.result.criterion_results
                    ],
                    executed_at=execution.executed_at,
                )
                for execution in report.validations
            ],
        )


class ErrorWebResponse(BaseModel):
    """Error detail schema."""

    code: str
    message: str
    details: str | None = None


class ErrorListWebResponse(BaseModel):
    """Error response schema."""

    errors: list[ErrorWebResponse]
