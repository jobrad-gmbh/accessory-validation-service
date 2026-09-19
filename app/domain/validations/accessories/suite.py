"""The business validations included in the accessory validation suite."""

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
from app.domain.validations.accessories.leasability.criteria import LeasabilityCriteria


def build_accessory_validation_service() -> ProductValidationService:
    """Build the accessory suite in execution order."""
    criteria = LeasabilityCriteria(
        explicitly_not_leasable_type=ExplicitlyNotLeasableAccessoryTypeCriterion(),
        special_rules=SpecialRulesCriterion(),
        explicitly_leasable_type=ExplicitlyLeasableAccessoryTypeCriterion(),
        technical_bicycle_component=TechnicalBicycleComponentCriterion(),
        stvzo_equipment=StvzoEquipmentCriterion(),
        functional_unit_with_bicycle=FunctionalUnitWithBicycleCriterion(),
        installable_on_bicycle=InstallableOnBicycleCriterion(),
    )
    return ProductValidationService([AccessoryLeasabilityValidation(criteria)])
