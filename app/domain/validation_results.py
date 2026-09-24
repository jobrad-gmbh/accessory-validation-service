from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID, uuid4

from app.domain.criterion import CriterionResult, SpecialRuleResult
from app.domain.product import (
    Product,
)


class ValidationStatus(StrEnum):
    PASSED = "PASSED"
    REJECTED = "REJECTED"
    UNDETERMINED = "UNDETERMINED"


class ReportStatus(StrEnum):
    VALID = "VALID"
    INVALID = "INVALID"
    UNDETERMINED = "UNDETERMINED"


@dataclass(frozen=True, kw_only=True)
class ValidationResult:
    """The business answer produced by a validation.

    Criterion results are optional and listed in evaluation order.
    """

    status: ValidationStatus
    details: str
    criterion_results: tuple[CriterionResult | SpecialRuleResult, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.status, ValidationStatus):
            raise ValueError("Validation result requires a ValidationStatus")
        if not isinstance(self.details, str) or not self.details.strip():
            raise ValueError("Validation result details cannot be blank")
        object.__setattr__(self, "criterion_results", tuple(self.criterion_results))
        if any(
            not isinstance(result, (CriterionResult, SpecialRuleResult))
            or not result.criterion_id
            for result in self.criterion_results
        ):
            raise ValueError("Validation criterion results require identified criterion results")


@dataclass(frozen=True, kw_only=True)
class ValidationExecution:
    """Complete historical execution of one validation for one product."""

    product: Product
    validation_id: str
    result: ValidationResult
    id: UUID = field(default_factory=uuid4)
    executed_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def __post_init__(self) -> None:
        if not self.validation_id.strip():
            raise ValueError("Validation execution requires a validation id")
        if self.executed_at.tzinfo is None or self.executed_at.utcoffset() is None:
            raise ValueError("Validation executed_at must include a timezone")


@dataclass(frozen=True, kw_only=True)
class ValidationReport:
    product: Product
    status: ReportStatus
    validations: tuple[ValidationExecution, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "validations", tuple(self.validations))
        if any(execution.product.id != self.product.id for execution in self.validations):
            raise ValueError("Every validation must belong to the report product")
