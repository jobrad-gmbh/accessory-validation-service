from collections.abc import Sequence

from app.domain.validation.errors import ValidationConfigurationError, ValidationExecutionError
from app.domain.validation.request import ValidationRequest
from app.domain.validation.results import (
    ReportStatus,
    ValidationExecution,
    ValidationReport,
    ValidationStatus,
)
from app.domain.validation.validation import Validation


class ProductValidationService:
    """Run the supplied checks in order and aggregate their business outcomes.

    All supplied checks run even after a business rejection. Technical errors
    stop execution. Resolution and strategies belong to individual checks.
    """

    def __init__(self, validations: Sequence[Validation]) -> None:
        self._validations = tuple(validations)
        ids = [validation.id for validation in self._validations]
        if not ids or any(not value.strip() for value in ids) or len(ids) != len(set(ids)):
            raise ValidationConfigurationError(
                "At least one validation with a unique, non-empty id is required"
            )

    async def validate(self, request: ValidationRequest) -> ValidationReport:
        executions: list[ValidationExecution] = []
        for validation in self._validations:
            try:
                execution = await validation.validate(request)
                if not isinstance(execution, ValidationExecution):
                    raise TypeError("Validation must return a ValidationExecution")
                if execution.validation_id != validation.id:
                    raise TypeError("Validation execution id does not match the validation")
                if execution.product.id != request.product.id:
                    raise TypeError("Validation execution does not belong to the validated product")
            except (ValidationConfigurationError, ValidationExecutionError):
                raise
            except Exception as exc:
                raise ValidationExecutionError(f"Validation {validation.id} failed") from exc
            executions.append(execution)

        if any(
            execution.result.status is ValidationStatus.REJECTED
            for execution in executions
        ):
            status = ReportStatus.INVALID
        elif all(
            execution.result.status is ValidationStatus.PASSED
            for execution in executions
        ):
            status = ReportStatus.VALID
        else:
            status = ReportStatus.UNDETERMINED
        return ValidationReport(
            product=request.product,
            status=status,
            validations=tuple(executions),
        )
