"""The business validations included in the accessory validation suite."""

from app.domain.validation_service import (
    ProductValidationService,
)
from app.domain.validations.accessories.leasability import (
    AccessoryLeasabilityValidation,
)


def build_accessory_validation_service() -> ProductValidationService:
    """Build the accessory suite in execution order."""
    return ProductValidationService([AccessoryLeasabilityValidation()])
