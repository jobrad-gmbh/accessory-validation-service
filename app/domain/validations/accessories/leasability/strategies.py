"""Standard and BAWU leasability flows expressed as ordinary Python."""

from app.domain.criterion import Criterion, CriterionAnswer, CriterionResult
from app.domain.errors import ValidationExecutionError
from app.domain.validation import ValidationRequest
from app.domain.validation_results import ValidationResult, ValidationStatus
from app.domain.validations.accessories.leasability.criteria import LeasabilityCriteria


async def standard_leasability_strategy(
    request: ValidationRequest, criteria: LeasabilityCriteria
) -> ValidationResult:
    if (
        await _answer(criteria.explicitly_not_leasable_type, request)
        is CriterionAnswer.YES
    ):
        # An excluded type needs an explicit exception; UNKNOWN still rejects.
        special = await _answer(criteria.special_rules, request)
        return _result(special is CriterionAnswer.YES)

    if await _answer(criteria.explicitly_leasable_type, request) is CriterionAnswer.YES:
        # An allowed type stays allowed unless special rules explicitly reject it.
        special = await _answer(criteria.special_rules, request)
        return _result(special is not CriterionAnswer.NO)

    if (
        await _answer(criteria.technical_bicycle_component, request)
        is CriterionAnswer.YES
    ):
        return _result(True)

    if await _answer(criteria.stvzo_equipment, request) is CriterionAnswer.YES:
        return _result(True)

    if (
        await _answer(criteria.functional_unit_with_bicycle, request)
        is CriterionAnswer.YES
    ):
        return _result(True)

    installable = await _answer(criteria.installable_on_bicycle, request)
    return _result(installable is CriterionAnswer.YES)


async def bawu_leasability_strategy(
    request: ValidationRequest, criteria: LeasabilityCriteria
) -> ValidationResult:
    if (
        await _answer(criteria.explicitly_not_leasable_type, request)
        is CriterionAnswer.YES
    ):
        # An excluded type needs an explicit exception; UNKNOWN still rejects.
        special = await _answer(criteria.special_rules, request)
        return _result(special is CriterionAnswer.YES)

    if await _answer(criteria.explicitly_leasable_type, request) is CriterionAnswer.YES:
        # An allowed type stays allowed unless special rules explicitly reject it.
        special = await _answer(criteria.special_rules, request)
        return _result(special is not CriterionAnswer.NO)

    if (
        await _answer(criteria.technical_bicycle_component, request)
        is CriterionAnswer.YES
    ):
        return _result(True)

    if (
        await _answer(criteria.functional_unit_with_bicycle, request)
        is CriterionAnswer.YES
    ):
        return _result(True)

    installable = await _answer(criteria.installable_on_bicycle, request)
    return _result(installable is CriterionAnswer.YES)


async def _answer(criterion: Criterion, request: ValidationRequest) -> CriterionAnswer:
    try:
        result = await criterion.evaluate(request)
        if not isinstance(result, CriterionResult) or not isinstance(
            result.answer, CriterionAnswer
        ):
            raise TypeError("Criterion returned an unsupported answer")
        return result.answer
    except Exception as exc:
        raise ValidationExecutionError(f"Criterion {criterion.id} failed") from exc


def _result(leasable: bool) -> ValidationResult:
    return ValidationResult(
        status=ValidationStatus.PASSED if leasable else ValidationStatus.REJECTED,
        details=(
            "El accesorio es financiable."
            if leasable
            else "El accesorio no es financiable."
        ),
    )
