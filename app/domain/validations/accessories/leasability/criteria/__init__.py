from dataclasses import dataclass

from app.domain.criterion import Criterion
from app.domain.validations.accessories.leasability.criteria.accessory_type import (
    ExplicitlyLeasableAccessoryTypeCriterion,
    ExplicitlyNotLeasableAccessoryTypeCriterion,
)
from app.domain.validations.accessories.leasability.criteria.bicycle_relationship import (
    FunctionalUnitWithBicycleCriterion,
    InstallableOnBicycleCriterion,
    StvzoEquipmentCriterion,
    TechnicalBicycleComponentCriterion,
)
from app.domain.validations.accessories.leasability.criteria.special_rules import (
    SpecialRulesCriterion,
)

__all__ = [
    "LeasabilityCriteria",
    "ExplicitlyLeasableAccessoryTypeCriterion",
    "ExplicitlyNotLeasableAccessoryTypeCriterion",
    "FunctionalUnitWithBicycleCriterion",
    "InstallableOnBicycleCriterion",
    "SpecialRulesCriterion",
    "StvzoEquipmentCriterion",
    "TechnicalBicycleComponentCriterion",
]


@dataclass(frozen=True, kw_only=True)
class LeasabilityCriteria:
    """Explicit dependencies for the accessory leasability flows."""

    explicitly_not_leasable_type: Criterion
    explicitly_leasable_type: Criterion
    special_rules: Criterion
    technical_bicycle_component: Criterion
    stvzo_equipment: Criterion
    functional_unit_with_bicycle: Criterion
    installable_on_bicycle: Criterion
