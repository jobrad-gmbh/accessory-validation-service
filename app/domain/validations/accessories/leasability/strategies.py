"""Standard and BAWU leasability flows expressed as ordinary Python."""

from app.adapters.llm import LLMClient
from app.domain.criterion import CriterionAnswer, SpecialRuleResult
from app.domain.validation import ValidationRequest
from app.domain.validation_results import ValidationResult, ValidationStatus
from app.domain.validations.accessories.product_information import (
    AccessoryProductInformation,
)
from app.domain.validations.accessories.leasability.criteria import (
    ExplicitlyNotLeasableAccessoryTypeCriterion,
    ExplicitlyLeasableAccessoryTypeCriterion,
    SpecialRulesCriterion,
    TechnicalBicycleComponentCriterion,
    StvzoEquipmentCriterion,
    FunctionalUnitWithBicycleCriterion,
    PermanentlyMountedCriterion,
)


async def standard_leasability_strategy(
    request: ValidationRequest,
    litellm_client: LLMClient,
    product_information: AccessoryProductInformation,
) -> ValidationResult:
    if (
        await ExplicitlyNotLeasableAccessoryTypeCriterion(litellm_client).evaluate(
            request, product_information
        )
    ).answer is CriterionAnswer.YES:
        special = await SpecialRulesCriterion(litellm_client).evaluate(
            request, product_information
        )
        return _result(_apply_special_rule(False, special))

    if (
        await ExplicitlyLeasableAccessoryTypeCriterion(litellm_client).evaluate(
            request, product_information
        )
    ).answer is CriterionAnswer.YES:
        special = await SpecialRulesCriterion(litellm_client).evaluate(
            request, product_information
        )
        return _result(_apply_special_rule(True, special))

    if (
        await TechnicalBicycleComponentCriterion(litellm_client).evaluate(
            request, product_information
        )
    ).answer is CriterionAnswer.YES:
        return _result(True)

    if (
        await StvzoEquipmentCriterion(litellm_client).evaluate(
            request, product_information
        )
    ).answer is CriterionAnswer.YES:
        return _result(True)

    if (
        await FunctionalUnitWithBicycleCriterion(litellm_client).evaluate(
            request, product_information
        )
    ).answer is CriterionAnswer.YES:
        return _result(True)

    installable = (
        await PermanentlyMountedCriterion(litellm_client).evaluate(
            request, product_information
        )
    ).answer
    return _result(installable is CriterionAnswer.YES)


async def bawu_leasability_strategy(
    request: ValidationRequest,
    litellm_client: LLMClient,
    product_information: AccessoryProductInformation,
) -> ValidationResult:
    if (
        await ExplicitlyNotLeasableAccessoryTypeCriterion(litellm_client).evaluate(
            request, product_information
        )
    ).answer is CriterionAnswer.YES:
        special = await SpecialRulesCriterion(litellm_client).evaluate(
            request, product_information
        )
        return _result(_apply_special_rule(False, special))

    if (
        await ExplicitlyLeasableAccessoryTypeCriterion(litellm_client).evaluate(
            request, product_information
        )
    ).answer is CriterionAnswer.YES:
        special = await SpecialRulesCriterion(litellm_client).evaluate(
            request, product_information
        )
        return _result(_apply_special_rule(True, special))

    if (
        await TechnicalBicycleComponentCriterion(litellm_client).evaluate(
            request, product_information
        )
    ).answer is CriterionAnswer.YES:
        return _result(True)

    if (
        await FunctionalUnitWithBicycleCriterion(litellm_client).evaluate(
            request, product_information
        )
    ).answer is CriterionAnswer.YES:
        return _result(True)

    installable = (
        await PermanentlyMountedCriterion(litellm_client).evaluate(
            request, product_information
        )
    ).answer
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


def _apply_special_rule(
    default_leasable: bool, special_rule: SpecialRuleResult
) -> bool:
    if special_rule.answer is not CriterionAnswer.YES:
        return default_leasable
    return special_rule.leasable is CriterionAnswer.YES
