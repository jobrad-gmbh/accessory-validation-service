from decimal import Decimal
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.domain.products import Product, ProductContext, ProductOrigin, ProductType
from app.domain.validation import (
    ReportStatus,
    ValidationReport,
    ValidationStatus,
)
from app.domain.validation.results import EvidenceValue
from app.domain.validation.request import ValidationRequest


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
    color: str | None = None
    size: str | None = None

    def to_domain(self) -> ValidationRequest:
        return ValidationRequest(
            product=Product(
                product_type=ProductType.ACCESSORY,
                brand=self.brand,
                model=self.model,
                price=self.price,
                color=self.color,
                size=self.size,
                origin=ProductOrigin(
                    source=self.origin.source,
                    external_ref=self.origin.external_ref,
                ),
            ),
            context=self.context,
        )


class ValidationResponse(BaseModel):
    """Public result of one validation execution."""

    id: UUID
    validation_id: str
    status: ValidationStatus
    reason_code: str
    details: str
    evidence: dict[str, EvidenceValue]
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
                    reason_code=execution.result.reason_code,
                    details=execution.result.details,
                    evidence=dict(execution.result.evidence),
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
