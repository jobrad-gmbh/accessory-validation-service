"""The business validations included in the accessory validation suite."""

from app.domain.validation import (
    ValidationRequest,
)
from app.domain.validation_service import (
    ProductValidationService,
)
from app.domain.validations.accessories.leasability import (
    AccessoryLeasabilityValidation,
    ExplicitlyLeasableAccessoryTypeCriterion,
    ExplicitlyNotLeasableAccessoryTypeCriterion,
    FunctionalUnitWithBicycleCriterion,
    InstallableOnBicycleCriterion,
    SpecialRulesCriterion,
    StvzoEquipmentCriterion,
    TechnicalBicycleComponentCriterion,
)
from app.shared.decision_strategies.contracts import Criterion


def build_accessory_validation_service() -> ProductValidationService:
    """Build the accessory suite in execution order."""
    criteria: list[Criterion[ValidationRequest]] = [
        ExplicitlyNotLeasableAccessoryTypeCriterion(),
        SpecialRulesCriterion(),
        ExplicitlyLeasableAccessoryTypeCriterion(),
        TechnicalBicycleComponentCriterion(),
        StvzoEquipmentCriterion(),
        FunctionalUnitWithBicycleCriterion(),
        InstallableOnBicycleCriterion(),
    ]
    return ProductValidationService([AccessoryLeasabilityValidation(criteria)])
