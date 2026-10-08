"""Standard and BAWU leasability flows expressed as ordinary Python."""

from collections.abc import Mapping
from typing import Protocol

from app.adapters.llm import LLMClient, LLMModelSettings
from app.domain.criterion import CriterionAnswer, CriterionResult
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


async def leasability_strategy(
    request: ValidationRequest,
    litellm_client: LLMClient,
    product_information: AccessoryProductInformation,
    criterion_settings: Mapping[str, LLMModelSettings] | None = None,
    *,
    validation_id: str | None = None,
    is_bawu: bool = False,
) -> ValidationResult:
    """Run the shared flow, using BAWU prompts and skipping StVZO when requested."""
    collector = _CriterionResultCollector(criterion_settings, validation_id)
    not_leasable = await collector.run(
        ExplicitlyNotLeasableAccessoryTypeCriterion(litellm_client, is_bawu=is_bawu),
        request,
        product_information,
    )
    if not_leasable.answer is CriterionAnswer.YES:
        special_rule = await collector.run(
            SpecialRulesCriterion(litellm_client, is_bawu=is_bawu),
            request,
            product_information,
        )
        return _apply_special_rule(False, not_leasable, special_rule, collector)

    leasable = await collector.run(
        ExplicitlyLeasableAccessoryTypeCriterion(litellm_client, is_bawu=is_bawu),
        request,
        product_information,
    )
    if leasable.answer is CriterionAnswer.YES:
        special_rule = await collector.run(
            SpecialRulesCriterion(litellm_client, is_bawu=is_bawu),
            request,
            product_information,
        )
        return _apply_special_rule(True, leasable, special_rule, collector)

    special_rule = await collector.run(
        SpecialRulesCriterion(litellm_client, is_bawu=is_bawu),
        request,
        product_information,
    )
    if special_rule.answer is not CriterionAnswer.UNKNOWN:
        return _result(
            special_rule.answer is CriterionAnswer.YES, special_rule, collector
        )

    technical_component = await collector.run(
        TechnicalBicycleComponentCriterion(litellm_client), request, product_information
    )
    if technical_component.answer is CriterionAnswer.YES:
        return _result(True, technical_component, collector)

    if not is_bawu:
        stvzo_required = await collector.run(
            StvzoEquipmentCriterion(litellm_client), request, product_information
        )
        if stvzo_required.answer is CriterionAnswer.YES:
            return _result(True, stvzo_required, collector)

    functional_unit = await collector.run(
        FunctionalUnitWithBicycleCriterion(litellm_client, is_bawu=is_bawu),
        request,
        product_information,
    )
    if functional_unit.answer is CriterionAnswer.YES:
        return _result(True, functional_unit, collector)

    permanently_mounted = await collector.run(
        PermanentlyMountedCriterion(litellm_client), request, product_information
    )
    if permanently_mounted.answer is CriterionAnswer.YES:
        return _result(True, permanently_mounted, collector)
    return _no_qualifying_criterion_result(collector, is_bawu=is_bawu)


async def standard_leasability_strategy(
    request: ValidationRequest,
    litellm_client: LLMClient,
    product_information: AccessoryProductInformation,
    criterion_settings: Mapping[str, LLMModelSettings] | None = None,
    *,
    validation_id: str | None = None,
) -> ValidationResult:
    return await leasability_strategy(
        request,
        litellm_client,
        product_information,
        criterion_settings,
        validation_id=validation_id,
        is_bawu=False,
    )


async def bawu_leasability_strategy(
    request: ValidationRequest,
    litellm_client: LLMClient,
    product_information: AccessoryProductInformation,
    criterion_settings: Mapping[str, LLMModelSettings] | None = None,
    *,
    validation_id: str | None = None,
) -> ValidationResult:
    return await leasability_strategy(
        request,
        litellm_client,
        product_information,
        criterion_settings,
        validation_id=validation_id,
        is_bawu=True,
    )


class _LeasabilityCriterion(Protocol):
    id: str

    async def evaluate(
        self,
        request: ValidationRequest,
        product_information: AccessoryProductInformation,
        *,
        settings: LLMModelSettings | None = None,
        validation_id: str | None = None,
    ) -> CriterionResult: ...


class _CriterionResultCollector:
    """Evaluate criteria with their settings and keep results in evaluation order."""

    def __init__(
        self,
        settings: Mapping[str, LLMModelSettings] | None = None,
        validation_id: str | None = None,
    ) -> None:
        self._settings = settings or {}
        self._validation_id = validation_id
        self._results: list[CriterionResult] = []

    async def run(
        self,
        criterion: _LeasabilityCriterion,
        request: ValidationRequest,
        product_information: AccessoryProductInformation,
    ) -> CriterionResult:
        outcome = await criterion.evaluate(
            request,
            product_information,
            settings=self._settings.get(criterion.id),
            validation_id=self._validation_id,
        )
        self._results.append(outcome)
        return outcome

    @property
    def results(self) -> tuple[CriterionResult, ...]:
        return tuple(self._results)


def _result(
    leasable: bool,
    source: CriterionResult,
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
    special_rule: CriterionResult,
    collector: _CriterionResultCollector,
) -> ValidationResult:
    if special_rule.answer is not CriterionAnswer.UNKNOWN:
        return _result(
            special_rule.answer is CriterionAnswer.YES, special_rule, collector
        )
    return _result(default_leasable, default_result, collector)
