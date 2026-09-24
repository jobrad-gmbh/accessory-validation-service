"""Standard and BAWU leasability flows expressed as ordinary Python."""

from typing import Protocol, TypeVar

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

CriterionOutcome = TypeVar(
    "CriterionOutcome", CriterionResult, SpecialRuleResult, covariant=True
)


async def standard_leasability_strategy(
    request: ValidationRequest,
    litellm_client: LLMClient,
    product_information: AccessoryProductInformation,
) -> ValidationResult:
    collector = _CriterionResultCollector()
    not_leasable = await collector.run(
        ExplicitlyNotLeasableAccessoryTypeCriterion(litellm_client),
        request,
        product_information,
    )
    if not_leasable.answer is CriterionAnswer.YES:
        special_rule = await collector.run(
            SpecialRulesCriterion(litellm_client), request, product_information
        )
        return _apply_special_rule(False, not_leasable, special_rule, collector)

    leasable = await collector.run(
        ExplicitlyLeasableAccessoryTypeCriterion(litellm_client),
        request,
        product_information,
    )
    if leasable.answer is CriterionAnswer.YES:
        special_rule = await collector.run(
            SpecialRulesCriterion(litellm_client), request, product_information
        )
        return _apply_special_rule(True, leasable, special_rule, collector)

    technical_component = await collector.run(
        TechnicalBicycleComponentCriterion(litellm_client), request, product_information
    )
    if technical_component.answer is CriterionAnswer.YES:
        return _result(True, technical_component, collector)

    stvzo_required = await collector.run(
        StvzoEquipmentCriterion(litellm_client), request, product_information
    )
    if stvzo_required.answer is CriterionAnswer.YES:
        return _result(True, stvzo_required, collector)

    functional_unit = await collector.run(
        FunctionalUnitWithBicycleCriterion(litellm_client), request, product_information
    )
    if functional_unit.answer is CriterionAnswer.YES:
        return _result(True, functional_unit, collector)

    permanently_mounted = await collector.run(
        PermanentlyMountedCriterion(litellm_client), request, product_information
    )
    if permanently_mounted.answer is CriterionAnswer.YES:
        return _result(True, permanently_mounted, collector)
    return _no_qualifying_criterion_result(collector, is_bawu=False)


async def bawu_leasability_strategy(
    request: ValidationRequest,
    litellm_client: LLMClient,
    product_information: AccessoryProductInformation,
) -> ValidationResult:
    collector = _CriterionResultCollector()
    not_leasable = await collector.run(
        ExplicitlyNotLeasableAccessoryTypeCriterion(litellm_client),
        request,
        product_information,
    )
    if not_leasable.answer is CriterionAnswer.YES:
        special_rule = await collector.run(
            SpecialRulesCriterion(litellm_client), request, product_information
        )
        return _apply_special_rule(False, not_leasable, special_rule, collector)

    leasable = await collector.run(
        ExplicitlyLeasableAccessoryTypeCriterion(litellm_client),
        request,
        product_information,
    )
    if leasable.answer is CriterionAnswer.YES:
        special_rule = await collector.run(
            SpecialRulesCriterion(litellm_client), request, product_information
        )
        return _apply_special_rule(True, leasable, special_rule, collector)

    technical_component = await collector.run(
        TechnicalBicycleComponentCriterion(litellm_client), request, product_information
    )
    if technical_component.answer is CriterionAnswer.YES:
        return _result(True, technical_component, collector)

    functional_unit = await collector.run(
        FunctionalUnitWithBicycleCriterion(litellm_client), request, product_information
    )
    if functional_unit.answer is CriterionAnswer.YES:
        return _result(True, functional_unit, collector)

    permanently_mounted = await collector.run(
        PermanentlyMountedCriterion(litellm_client), request, product_information
    )
    if permanently_mounted.answer is CriterionAnswer.YES:
        return _result(True, permanently_mounted, collector)
    return _no_qualifying_criterion_result(collector, is_bawu=True)


class _LeasabilityCriterion(Protocol[CriterionOutcome]):
    async def evaluate(
        self,
        request: ValidationRequest,
        product_information: AccessoryProductInformation,
    ) -> CriterionOutcome: ...


class _CriterionResultCollector:
    """Evaluate criteria and keep their results in evaluation order."""

    def __init__(self) -> None:
        self._results: list[CriterionResult | SpecialRuleResult] = []

    async def run(
        self,
        criterion: _LeasabilityCriterion[CriterionOutcome],
        request: ValidationRequest,
        product_information: AccessoryProductInformation,
    ) -> CriterionOutcome:
        outcome = await criterion.evaluate(request, product_information)
        self._results.append(outcome)
        return outcome

    @property
    def results(self) -> tuple[CriterionResult | SpecialRuleResult, ...]:
        return tuple(self._results)


def _result(
    leasable: bool,
    source: CriterionResult | SpecialRuleResult,
    collector: _CriterionResultCollector,
) -> ValidationResult:
    return ValidationResult(
        status=ValidationStatus.PASSED if leasable else ValidationStatus.REJECTED,
        details=source.details,
        criterion_results=collector.results,
    )


def _no_qualifying_criterion_result(
    collector: _CriterionResultCollector, *, is_bawu: bool
) -> ValidationResult:
    qualifying_types = (
        "a technical component, a functional unit with the bicycle, or a bike-mounted item"
        if is_bawu
        else "a technical component, StVZO-related equipment, a functional unit with the bicycle, or a bike-mounted item"
    )
    return ValidationResult(
        status=ValidationStatus.REJECTED,
        details=(
            "The accessory did not match an explicitly leasable type and was not "
            f"identified as {qualifying_types}."
        ),
        criterion_results=collector.results,
    )


def _apply_special_rule(
    default_leasable: bool,
    default_result: CriterionResult,
    special_rule: SpecialRuleResult,
    collector: _CriterionResultCollector,
) -> ValidationResult:
    if special_rule.answer is CriterionAnswer.YES:
        return _result(
            special_rule.leasable is CriterionAnswer.YES, special_rule, collector
        )
    return _result(default_leasable, default_result, collector)
