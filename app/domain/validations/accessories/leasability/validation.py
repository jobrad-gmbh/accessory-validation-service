from app.adapters.llm import LLMClient
from app.domain.validation import Validation, ValidationRequest
from app.domain.validation_results import ValidationResult
from app.domain.validations.accessories.product_information import (
    AccessoryProductInformationService,
)
from app.domain.validations.accessories.leasability.strategies import (
    bawu_leasability_strategy,
    standard_leasability_strategy,
)


class AccessoryLeasabilityValidation(Validation):
    """Select the leasability flow for the submitted order context."""

    id = "accessory_leasability"

    def __init__(
        self,
        litellm_client: LLMClient,
        product_information_service: AccessoryProductInformationService | None = None,
    ) -> None:
        self._litellm_client = litellm_client
        self._product_information_service = (
            product_information_service
            if product_information_service is not None
            else AccessoryProductInformationService(litellm_client)
        )

    async def evaluate_result(self, request: ValidationRequest) -> ValidationResult:
        product_information = await self._product_information_service.retrieve(
            request.product
        )
        if request.context.is_bawu_order:
            return await bawu_leasability_strategy(
                request, self._litellm_client, product_information
            )
        return await standard_leasability_strategy(
            request, self._litellm_client, product_information
        )
