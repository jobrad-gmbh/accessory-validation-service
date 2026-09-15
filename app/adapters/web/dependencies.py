from typing import Annotated

from fastapi import Depends

from app.domain.validation import ProductValidationService
from app.domain.validation.request import ValidationRequest
from app.domain.validation.accessory_leasability import (
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


def get_validation_service() -> ProductValidationService:
    """Build the validations currently exposed by the API."""
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


ValidationServiceDependency = Annotated[
    ProductValidationService,
    Depends(get_validation_service),
]
