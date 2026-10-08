from collections.abc import Mapping
from dataclasses import dataclass

from app.adapters.llm import LLMClient, LLMModelSettings
from app.domain.validation import Validation, ValidationRequest
from app.domain.validation_results import ValidationResult
from app.domain.validations.accessories.product_information import (
    AccessoryProductInformation,
    AccessoryProductInformationService,
)
from app.domain.validations.accessories.leasability.strategies import (
    bawu_leasability_strategy,
    standard_leasability_strategy,
)


@dataclass(frozen=True, kw_only=True)
class AccessoryLeasabilityResult(ValidationResult):
    """Leasability outcome and the product information used to evaluate it."""

    product_information: AccessoryProductInformation


class AccessoryLeasabilityValidation(Validation):
    """Select the leasability flow for the submitted order context."""

    id = "accessory_leasability"

    def __init__(
        self,
        litellm_client: LLMClient,
        product_information_service: AccessoryProductInformationService | None = None,
        criterion_settings: Mapping[str, LLMModelSettings] | None = None,
    ) -> None:
        self._litellm_client = litellm_client
        self._criterion_settings = dict(criterion_settings or {})
        self._product_information_service = (
            product_information_service
            if product_information_service is not None
            else AccessoryProductInformationService(litellm_client)
        )

    async def evaluate_result(
        self, request: ValidationRequest
    ) -> AccessoryLeasabilityResult:
        product_information = await self._product_information_service.retrieve(
            request.product, product_id=request.product.id, validation_id=self.id
        )
        strategy = (
            bawu_leasability_strategy
            if request.context.is_bawu_order
            else standard_leasability_strategy
        )
        result = await strategy(
            request,
            self._litellm_client,
            product_information,
            self._criterion_settings,
            validation_id=self.id,
        )
        return AccessoryLeasabilityResult(
            status=result.status,
            details=result.details,
            criterion_results=result.criterion_results,
            product_information=product_information,
        )
