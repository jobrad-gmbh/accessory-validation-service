"""Standard and BAWU leasability flows expressed as ordinary Python."""

from app.domain.criterion import CriterionAnswer
from app.domain.validation import ValidationRequest
from app.domain.validation_results import ValidationResult, ValidationStatus
from app.domain.validations.accessories.leasability.criteria import (
    ExplicitlyNotLeasableAccessoryTypeCriterion,
    ExplicitlyLeasableAccessoryTypeCriterion,
    SpecialRulesCriterion,
    TechnicalBicycleComponentCriterion,
    StvzoEquipmentCriterion,
    FunctionalUnitWithBicycleCriterion,
    InstallableOnBicycleCriterion,
)


async def standard_leasability_strategy(request: ValidationRequest) -> ValidationResult:
    if (
        await ExplicitlyNotLeasableAccessoryTypeCriterion().evaluate(request)
    ).answer is CriterionAnswer.YES:
        # An excluded type needs an explicit exception; UNKNOWN still rejects.
        special = (await SpecialRulesCriterion().evaluate(request)).answer
        return _result(special is CriterionAnswer.YES)

    if (
        await ExplicitlyLeasableAccessoryTypeCriterion().evaluate(request)
    ).answer is CriterionAnswer.YES:
        # An allowed type stays allowed unless special rules explicitly reject it.
        special = (await SpecialRulesCriterion().evaluate(request)).answer
        return _result(special is not CriterionAnswer.NO)

    if (
        await TechnicalBicycleComponentCriterion().evaluate(request)
    ).answer is CriterionAnswer.YES:
        return _result(True)

    if (
        await StvzoEquipmentCriterion().evaluate(request)
    ).answer is CriterionAnswer.YES:
        return _result(True)

    if (
        await FunctionalUnitWithBicycleCriterion().evaluate(request)
    ).answer is CriterionAnswer.YES:
        return _result(True)

    installable = (await InstallableOnBicycleCriterion().evaluate(request)).answer
    return _result(installable is CriterionAnswer.YES)


async def bawu_leasability_strategy(request: ValidationRequest) -> ValidationResult:
    if (
        await ExplicitlyNotLeasableAccessoryTypeCriterion().evaluate(request)
    ).answer is CriterionAnswer.YES:
        # An excluded type needs an explicit exception; UNKNOWN still rejects.
        special = (await SpecialRulesCriterion().evaluate(request)).answer
        return _result(special is CriterionAnswer.YES)

    if (
        await ExplicitlyLeasableAccessoryTypeCriterion().evaluate(request)
    ).answer is CriterionAnswer.YES:
        # An allowed type stays allowed unless special rules explicitly reject it.
        special = (await SpecialRulesCriterion().evaluate(request)).answer
        return _result(special is not CriterionAnswer.NO)

    if (
        await TechnicalBicycleComponentCriterion().evaluate(request)
    ).answer is CriterionAnswer.YES:
        return _result(True)

    if (
        await FunctionalUnitWithBicycleCriterion().evaluate(request)
    ).answer is CriterionAnswer.YES:
        return _result(True)

    installable = (await InstallableOnBicycleCriterion().evaluate(request)).answer
    return _result(installable is CriterionAnswer.YES)


def _result(leasable: bool) -> ValidationResult:
    return ValidationResult(
        status=ValidationStatus.PASSED if leasable else ValidationStatus.REJECTED,
        details=(
            "The accessory is leasable."
            if leasable
            else "The accessory is not leasable."
        ),
    )
