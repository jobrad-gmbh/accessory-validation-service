"""The business validations included in the accessory validation suite."""

from collections.abc import Mapping

from app.adapters.llm import LLMClient, LLMModelSettings
from app.domain.validation_service import (
    ProductValidationService,
)
from app.domain.validation_repository import ValidationReportRepository
from app.domain.validations.accessories.leasability import (
    AccessoryLeasabilityValidation,
)


def build_accessory_validation_service(
    litellm_client: LLMClient,
    repository: ValidationReportRepository,
    criterion_settings: Mapping[str, LLMModelSettings] | None = None,
) -> ProductValidationService:
    """Build the accessory suite in execution order."""
    return ProductValidationService(
        [
            AccessoryLeasabilityValidation(
                litellm_client, criterion_settings=criterion_settings
            )
        ],
        repository=repository,
    )
