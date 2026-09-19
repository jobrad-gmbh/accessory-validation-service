import asyncio
from unittest.mock import AsyncMock

import pytest

from app.domain.criterion import CriterionAnswer, CriterionResult
from app.domain.errors import ValidationExecutionError
from app.domain.product import Product, ProductContext, ProductOrigin, ProductType
from app.domain.validation import ValidationRequest
from app.domain.validation_results import ValidationStatus
from app.domain.validation_service import ProductValidationService
from app.domain.validations.accessories.leasability import strategies
from app.domain.validations.accessories.leasability.validation import (
    AccessoryLeasabilityValidation,
)

YES = CriterionAnswer.YES
NO = CriterionAnswer.NO
UNKNOWN = CriterionAnswer.UNKNOWN

ORDER = (
    "explicitly_not_leasable_type",
    "explicitly_leasable_type",
    "technical_bicycle_component",
    "stvzo_equipment",
    "functional_unit_with_bicycle",
    "installable_on_bicycle",
)


def request(is_bawu=False):
    return ValidationRequest(
        product=Product(
            product_type=ProductType.ACCESSORY,
            brand="Example",
            model="Rack",
            origin=ProductOrigin(source="odoo", external_ref="ACC-42"),
        ),
        context=ProductContext(is_bawu_order=is_bawu),
    )


def criteria_with_answers(monkeypatch, answers, calls, default=NO):
    async def evaluate(self, submitted):
        calls.append(self.id)
        return CriterionResult(
            answers.get(self.id, default), "Deterministic criterion answer."
        )

    for criterion in (
        strategies.ExplicitlyNotLeasableAccessoryTypeCriterion,
        strategies.ExplicitlyLeasableAccessoryTypeCriterion,
        strategies.SpecialRulesCriterion,
        strategies.TechnicalBicycleComponentCriterion,
        strategies.StvzoEquipmentCriterion,
        strategies.FunctionalUnitWithBicycleCriterion,
        strategies.InstallableOnBicycleCriterion,
    ):
        monkeypatch.setattr(criterion, "evaluate", evaluate)


@pytest.mark.parametrize("is_bawu", [False, True])
@pytest.mark.parametrize("excluded", [False, True])
@pytest.mark.parametrize("special", [YES, NO, UNKNOWN])
def test_special_rules_preserve_type_specific_outcomes(
    monkeypatch, is_bawu, excluded, special
):
    type_check = ORDER[0] if excluded else ORDER[1]
    calls = []
    criteria_with_answers(
        monkeypatch, {type_check: YES, "special_rules": special}, calls
    )
    submitted = request(is_bawu)
    execution = asyncio.run(AccessoryLeasabilityValidation().validate(submitted))

    passed = special is YES if excluded else special is not NO
    assert execution.result.status is (
        ValidationStatus.PASSED if passed else ValidationStatus.REJECTED
    )
    assert execution.product is submitted.product
    assert execution.validation_id == "accessory_leasability"
    assert calls == ([ORDER[0]] if excluded else list(ORDER[:2])) + ["special_rules"]


@pytest.mark.parametrize("is_bawu", [False, True])
@pytest.mark.parametrize("default", [NO, UNKNOWN])
@pytest.mark.parametrize("accepting_criterion", [None, *ORDER[2:]])
def test_fallback_checks_short_circuit_and_bawu_skips_stvzo(
    monkeypatch, is_bawu, default, accepting_criterion
):
    calls = []
    answers = {accepting_criterion: YES} if accepting_criterion else {}
    criteria_with_answers(monkeypatch, answers, calls, default)
    execution = asyncio.run(AccessoryLeasabilityValidation().validate(request(is_bawu)))

    applicable = [name for name in ORDER if not (is_bawu and name == "stvzo_equipment")]
    passed = accepting_criterion in applicable
    expected_calls = (
        applicable[: applicable.index(accepting_criterion) + 1]
        if passed
        else applicable
    )
    assert calls == expected_calls
    assert execution.result.status is (
        ValidationStatus.PASSED if passed else ValidationStatus.REJECTED
    )
    assert execution.result.details == (
        "The accessory is leasable." if passed else "The accessory is not leasable."
    )


def test_criterion_failures_are_technical_errors(monkeypatch):
    calls = []
    criteria_with_answers(monkeypatch, {}, calls)
    failure = RuntimeError("Provider unavailable")
    monkeypatch.setattr(
        strategies.ExplicitlyNotLeasableAccessoryTypeCriterion,
        "evaluate",
        AsyncMock(side_effect=failure),
    )
    service = ProductValidationService([AccessoryLeasabilityValidation()])
    with pytest.raises(
        ValidationExecutionError, match="Validation accessory_leasability failed"
    ) as exc:
        asyncio.run(service.validate(request()))
    assert exc.value.__cause__ is failure
    assert calls == []
