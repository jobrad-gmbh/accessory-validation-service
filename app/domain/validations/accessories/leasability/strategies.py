"""Standard and BAWU leasability flows expressed as ordinary Python."""

from app.adapters.llm import LLMClient
from app.domain.criterion import CriterionAnswer, CriterionResult, SpecialRuleResult
from app.domain.validation import ValidationRequest
from app.domain.validation_results import ValidationResult, ValidationStatus
from app.domain.validations.accessories.leasability.criteria import (
    ExplicitlyLeasableAccessoryTypeCriterion,
    ExplicitlyNotLeasableAccessoryTypeCriterion,
    FunctionalUnitWithBicycleCriterion,
    PermanentlyMountedCriterion,
    SpecialRulesCriterion,
    StvzoEquipmentCriterion,
    TechnicalBicycleComponentCriterion,
)
from app.domain.validations.accessories.product_information import (
    AccessoryProductInformation,
)


async def standard_leasability_strategy(
    request: ValidationRequest,
    litellm_client: LLMClient,
    product_information: AccessoryProductInformation,
) -> ValidationResult:
    not_leasable = await ExplicitlyNotLeasableAccessoryTypeCriterion(
        litellm_client
    ).evaluate(request, product_information)
    if not_leasable.answer is CriterionAnswer.YES:
        special_rule = await SpecialRulesCriterion(litellm_client).evaluate(
            request, product_information
        )
        return _apply_special_rule(False, not_leasable, special_rule)

    leasable = await ExplicitlyLeasableAccessoryTypeCriterion(litellm_client).evaluate(
        request, product_information
    )
    if leasable.answer is CriterionAnswer.YES:
        special_rule = await SpecialRulesCriterion(litellm_client).evaluate(
            request, product_information
        )
        return _apply_special_rule(True, leasable, special_rule)

    technical_component = await TechnicalBicycleComponentCriterion(
        litellm_client
    ).evaluate(request, product_information)
    if technical_component.answer is CriterionAnswer.YES:
        return _result(True, technical_component)

    stvzo_required = await StvzoEquipmentCriterion(litellm_client).evaluate(
        request, product_information
    )
    if stvzo_required.answer is CriterionAnswer.YES:
        return _result(True, stvzo_required)

    functional_unit = await FunctionalUnitWithBicycleCriterion(litellm_client).evaluate(
        request, product_information
    )
    if functional_unit.answer is CriterionAnswer.YES:
        return _result(True, functional_unit)

    permanently_mounted = await PermanentlyMountedCriterion(litellm_client).evaluate(
        request, product_information
    )
    return _result(
        permanently_mounted.answer is CriterionAnswer.YES,
        permanently_mounted,
    )


async def bawu_leasability_strategy(
    request: ValidationRequest,
    litellm_client: LLMClient,
    product_information: AccessoryProductInformation,
) -> ValidationResult:
    not_leasable = await ExplicitlyNotLeasableAccessoryTypeCriterion(
        litellm_client
    ).evaluate(request, product_information)
    if not_leasable.answer is CriterionAnswer.YES:
        special_rule = await SpecialRulesCriterion(litellm_client).evaluate(
            request, product_information
        )
        return _apply_special_rule(False, not_leasable, special_rule)

    leasable = await ExplicitlyLeasableAccessoryTypeCriterion(litellm_client).evaluate(
        request, product_information
    )
    if leasable.answer is CriterionAnswer.YES:
        special_rule = await SpecialRulesCriterion(litellm_client).evaluate(
            request, product_information
        )
        return _apply_special_rule(True, leasable, special_rule)

    technical_component = await TechnicalBicycleComponentCriterion(
        litellm_client
    ).evaluate(request, product_information)
    if technical_component.answer is CriterionAnswer.YES:
        return _result(True, technical_component)

    functional_unit = await FunctionalUnitWithBicycleCriterion(litellm_client).evaluate(
        request, product_information
    )
    if functional_unit.answer is CriterionAnswer.YES:
        return _result(True, functional_unit)

    permanently_mounted = await PermanentlyMountedCriterion(litellm_client).evaluate(
        request, product_information
    )
    return _result(
        permanently_mounted.answer is CriterionAnswer.YES,
        permanently_mounted,
    )


def _result(
    leasable: bool,
    source: CriterionResult | SpecialRuleResult,
) -> ValidationResult:
    return ValidationResult(
        status=ValidationStatus.PASSED if leasable else ValidationStatus.REJECTED,
        details=source.details,
    )


def _apply_special_rule(
    default_leasable: bool,
    default_result: CriterionResult,
    special_rule: SpecialRuleResult,
) -> ValidationResult:
    if special_rule.answer is CriterionAnswer.YES:
        return _result(special_rule.leasable is CriterionAnswer.YES, special_rule)
    return _result(default_leasable, default_result)
