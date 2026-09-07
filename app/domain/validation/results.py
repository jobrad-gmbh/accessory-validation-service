from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from types import MappingProxyType
from uuid import UUID, uuid4

from app.domain.products.product import Product
from app.shared.decision_strategies.results import StrategyEvaluation

EvidenceValue = str | bool | int | None


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
    """The business answer produced by a validation."""

    status: ValidationStatus
    reason_code: str
    details: str
    evidence: Mapping[str, EvidenceValue] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not isinstance(self.status, ValidationStatus):
            raise ValueError("Validation result requires a ValidationStatus")
        for name in ("reason_code", "details"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"Validation result {name} cannot be blank")
        object.__setattr__(self, "evidence", MappingProxyType(dict(self.evidence)))


@dataclass(frozen=True, kw_only=True)
class ValidationExecution:
    """Complete historical execution of one validation for one product."""

    product: Product
    validation_id: str
    result: ValidationResult
    strategy_evaluations: tuple[StrategyEvaluation, ...] = ()
    id: UUID = field(default_factory=uuid4)
    executed_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def __post_init__(self) -> None:
        if not self.validation_id.strip():
            raise ValueError("Validation execution requires a validation id")
        if self.executed_at.tzinfo is None or self.executed_at.utcoffset() is None:
            raise ValueError("Validation executed_at must include a timezone")
        object.__setattr__(self, "strategy_evaluations", tuple(self.strategy_evaluations))


@dataclass(frozen=True, kw_only=True)
class ValidationReport:
    product: Product
    status: ReportStatus
    validations: tuple[ValidationExecution, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "validations", tuple(self.validations))
        if any(execution.product.id != self.product.id for execution in self.validations):
            raise ValueError("Every validation must belong to the report product")
