from app.domain.validation import Validation, ValidationRequest
from app.domain.validation_results import ValidationResult
from app.domain.validations.accessories.leasability.strategies import (
    bawu_leasability_strategy,
    standard_leasability_strategy,
)


class AccessoryLeasabilityValidation(Validation):
    """Select the leasability flow for the submitted order context."""

    id = "accessory_leasability"

    async def evaluate_result(self, request: ValidationRequest) -> ValidationResult:
        if request.context.is_bawu_order:
            return await bawu_leasability_strategy(request)
        return await standard_leasability_strategy(request)
