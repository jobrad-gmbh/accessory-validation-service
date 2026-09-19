from app.domain.validation import SimpleValidation, ValidationRequest
from app.domain.validation_results import ValidationResult
from app.domain.validations.accessories.leasability.criteria import LeasabilityCriteria
from app.domain.validations.accessories.leasability.strategies import (
    bawu_leasability_strategy,
    standard_leasability_strategy,
)


class AccessoryLeasabilityValidation(SimpleValidation):
    """Select the leasability flow for the submitted order context."""

    id = "accessory_leasability"

    def __init__(self, criteria: LeasabilityCriteria) -> None:
        self._criteria = criteria

    async def evaluate_result(self, request: ValidationRequest) -> ValidationResult:
        if request.context.is_bawu_order:
            return await bawu_leasability_strategy(request, self._criteria)
        return await standard_leasability_strategy(request, self._criteria)
