import asyncio
import json
from unittest.mock import AsyncMock

import pytest
from pydantic import BaseModel

from app.adapters.llm import LiteLLMConfig
from app.domain.criterion import CriterionAnswer, CriterionResult, SpecialRuleResult
from app.domain.errors import ValidationExecutionError
from app.domain.product import Product, ProductContext, ProductOrigin, ProductType
from app.domain.validation import ValidationRequest
from app.domain.validation_results import ValidationStatus
from app.domain.validation_service import ProductValidationService
from app.domain.validations.accessories.leasability import strategies
from app.domain.validations.accessories.leasability import criteria
from app.domain.validations.accessories.leasability.validation import (
    AccessoryLeasabilityValidation,
)
from app.domain.validations.accessories.product_information import (
    AccessoryProductInformation,
    AccessoryProductInformationService,
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
    "permanently_mounted",
)

PRODUCT_INFORMATION = AccessoryProductInformation(
    summary="A fixed rear bicycle rack for carrying panniers.",
    model="search-model",
    used_web_search=True,
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


def validation():
    information_service = AsyncMock(spec=AccessoryProductInformationService)
    information_service.retrieve.return_value = PRODUCT_INFORMATION
    return AccessoryLeasabilityValidation(AsyncMock(), information_service)


def criteria_with_answers(monkeypatch, answers, calls, default=NO):
    async def evaluate(self, submitted, product_information):
        assert product_information is PRODUCT_INFORMATION
        calls.append(self.id)
        configured = answers.get(self.id, default)
        if isinstance(configured, (CriterionResult, SpecialRuleResult)):
            return configured
        return CriterionResult(configured, "Deterministic criterion answer.")

    for criterion in (
        strategies.ExplicitlyNotLeasableAccessoryTypeCriterion,
        strategies.ExplicitlyLeasableAccessoryTypeCriterion,
        strategies.SpecialRulesCriterion,
        strategies.TechnicalBicycleComponentCriterion,
        strategies.StvzoEquipmentCriterion,
        strategies.FunctionalUnitWithBicycleCriterion,
        strategies.PermanentlyMountedCriterion,
    ):
        monkeypatch.setattr(criterion, "evaluate", evaluate)


def test_validation_retrieves_product_information_once(monkeypatch):
    calls = []
    criteria_with_answers(monkeypatch, {ORDER[0]: YES}, calls)
    information_service = AsyncMock(spec=AccessoryProductInformationService)
    information_service.retrieve.return_value = PRODUCT_INFORMATION
    submitted = request()

    asyncio.run(
        AccessoryLeasabilityValidation(
            AsyncMock(), information_service
        ).validate(submitted)
    )

    information_service.retrieve.assert_awaited_once_with(submitted.product)
    assert calls == [ORDER[0], "special_rules"]


@pytest.mark.parametrize("is_bawu", [False, True])
@pytest.mark.parametrize("excluded", [False, True])
@pytest.mark.parametrize(
    "special",
    [
        SpecialRuleResult(YES, YES, "A leasable special rule matched."),
        SpecialRuleResult(YES, NO, "A non-leasable special rule matched."),
        SpecialRuleResult(NO, UNKNOWN, "No special rule matched."),
        SpecialRuleResult(UNKNOWN, UNKNOWN, "The match could not be determined."),
    ],
)
def test_special_rules_preserve_type_specific_outcomes(
    monkeypatch, is_bawu, excluded, special
):
    type_check = ORDER[0] if excluded else ORDER[1]
    calls = []
    criteria_with_answers(
        monkeypatch, {type_check: YES, "special_rules": special}, calls
    )
    submitted = request(is_bawu)
    execution = asyncio.run(validation().validate(submitted))

    passed = special.leasable is YES if special.answer is YES else not excluded
    assert execution.result.status is (
        ValidationStatus.PASSED if passed else ValidationStatus.REJECTED
    )
    assert execution.product is submitted.product
    assert execution.validation_id == "accessory_leasability"
    assert calls == ([ORDER[0]] if excluded else list(ORDER[:2])) + ["special_rules"]
    assert execution.result.details == (
        special.details
        if special.answer is YES
        else "Deterministic criterion answer."
    )


@pytest.mark.parametrize("is_bawu", [False, True])
@pytest.mark.parametrize("default", [NO, UNKNOWN])
@pytest.mark.parametrize("accepting_criterion", [None, *ORDER[2:]])
def test_fallback_checks_short_circuit_and_bawu_skips_stvzo(
    monkeypatch, is_bawu, default, accepting_criterion
):
    calls = []
    answers = {accepting_criterion: YES} if accepting_criterion else {}
    criteria_with_answers(monkeypatch, answers, calls, default)
    execution = asyncio.run(validation().validate(request(is_bawu)))

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
    assert execution.result.details == "Deterministic criterion answer."


def test_decisive_criterion_provides_validation_details(monkeypatch):
    calls = []
    decisive = CriterionResult(YES, "The rack is a technical bicycle component.")
    criteria_with_answers(
        monkeypatch,
        {"technical_bicycle_component": decisive},
        calls,
    )

    execution = asyncio.run(validation().validate(request()))

    assert execution.result.status is ValidationStatus.PASSED
    assert execution.result.details == decisive.details


def test_criterion_failures_are_technical_errors(monkeypatch):
    calls = []
    criteria_with_answers(monkeypatch, {}, calls)
    failure = RuntimeError("Provider unavailable")
    monkeypatch.setattr(
        strategies.ExplicitlyNotLeasableAccessoryTypeCriterion,
        "evaluate",
        AsyncMock(side_effect=failure),
    )
    service = ProductValidationService([validation()])
    with pytest.raises(
        ValidationExecutionError, match="Validation accessory_leasability failed"
    ) as exc:
        asyncio.run(service.validate(request()))
    assert exc.value.__cause__ is failure
    assert calls == []


@pytest.mark.parametrize("answer", list(CriterionAnswer))
def test_explicitly_not_leasable_type_uses_llm_result(answer):
    client = AsyncMock()
    client.config = LiteLLMConfig(
        base_url="https://gateway.example/v1",
        models=("client-default",),
    )
    client.generate.return_value.text = json.dumps(
        {"answer": answer.value, "details": "Classification reason."}
    )

    result = asyncio.run(
        criteria.ExplicitlyNotLeasableAccessoryTypeCriterion(client).evaluate(
            request(), PRODUCT_INFORMATION
        )
    )

    assert result == CriterionResult(answer, "Classification reason.")
    product_payload = json.loads(client.generate.await_args.args[0])
    assert product_payload["brand"] == "Example"
    assert product_payload["model"] == "Rack"
    assert product_payload["product_information"] == {
        "summary": PRODUCT_INFORMATION.summary,
        "sources": [],
    }
    instructions = client.generate.await_args.kwargs["instructions"]
    assert "# Explicitly not-leasable accessory types" in instructions
    assert "Bicycle trailers" in instructions
    assert "The object must match this JSON Schema" in instructions
    schema = json.loads(instructions.rsplit("```json\n", 1)[1].removesuffix("```"))
    assert set(schema["properties"]) == {"answer", "details"}
    assert client.generate.await_args.kwargs["config"].models == criteria.DEFAULT_MODELS


def test_prompt_output_schema_is_selected_per_criterion():
    class RankedResponse(BaseModel):
        rank: int
        reason: str

    instructions = criteria.load_prompt(
        criteria.EXPLICITLY_NOT_LEASABLE_PROMPT_PATH, RankedResponse
    )

    schema = json.loads(instructions.rsplit("```json\n", 1)[1].removesuffix("```"))
    assert set(schema["properties"]) == {"rank", "reason"}


@pytest.mark.parametrize(
    "response",
    [
        "not json",
        '{"answer": "MAYBE", "details": "Unsure."}',
        '{"answer": "YES", "details": ""}',
        '{"answer": "YES", "details": "Valid", "extra": true}',
    ],
)
def test_explicitly_not_leasable_type_rejects_invalid_llm_result(response):
    client = AsyncMock()
    client.config = LiteLLMConfig(
        base_url="https://gateway.example/v1",
        models=("client-default",),
    )
    client.generate.return_value.text = response

    with pytest.raises(ValueError, match="invalid criterion response"):
        asyncio.run(
            criteria.ExplicitlyNotLeasableAccessoryTypeCriterion(client).evaluate(
                request(), PRODUCT_INFORMATION
            )
        )


@pytest.mark.parametrize("answer", list(CriterionAnswer))
def test_explicitly_leasable_type_uses_llm_result(answer):
    client = AsyncMock()
    client.config = LiteLLMConfig(
        base_url="https://gateway.example/v1",
        models=("client-default",),
    )
    client.generate.return_value.text = json.dumps(
        {"answer": answer.value, "details": "Classification reason."}
    )

    result = asyncio.run(
        criteria.ExplicitlyLeasableAccessoryTypeCriterion(client).evaluate(
            request(), PRODUCT_INFORMATION
        )
    )

    assert result == CriterionResult(answer, "Classification reason.")
    instructions = client.generate.await_args.kwargs["instructions"]
    assert "# Explicitly leasable accessory types" in instructions
    assert "Bike lock" in instructions
    assert client.generate.await_args.kwargs["config"].models == criteria.DEFAULT_MODELS


@pytest.mark.parametrize(
    "criterion_class,prompt_heading",
    [
        (criteria.TechnicalBicycleComponentCriterion, "# Technical bicycle components"),
        (criteria.StvzoEquipmentCriterion, "# StVZO-related equipment"),
        (criteria.FunctionalUnitWithBicycleCriterion, "# Functional units"),
        (criteria.PermanentlyMountedCriterion, "# Installation status"),
    ],
)
def test_remaining_criteria_use_llm_results(criterion_class, prompt_heading):
    client = AsyncMock()
    client.config = LiteLLMConfig(
        base_url="https://gateway.example/v1",
        models=("client-default",),
    )
    client.generate.return_value.text = (
        '{"answer": "YES", "details": "Classification reason."}'
    )

    result = asyncio.run(
        criterion_class(client).evaluate(request(), PRODUCT_INFORMATION)
    )

    assert result == CriterionResult(YES, "Classification reason.")
    assert prompt_heading in client.generate.await_args.kwargs["instructions"]
    assert client.generate.await_args.kwargs["config"].models == criteria.DEFAULT_MODELS


@pytest.mark.parametrize(
    "answer,leasable",
    [
        (YES, YES),
        (YES, NO),
        (NO, UNKNOWN),
        (UNKNOWN, UNKNOWN),
    ],
)
def test_special_rules_use_leasability_result(answer, leasable):
    client = AsyncMock()
    client.config = LiteLLMConfig(
        base_url="https://gateway.example/v1",
        models=("client-default",),
    )
    client.generate.return_value.text = json.dumps(
        {
            "answer": answer.value,
            "leasable": leasable.value,
            "details": "Special-rule reason.",
        }
    )

    result = asyncio.run(
        criteria.SpecialRulesCriterion(client).evaluate(request(), PRODUCT_INFORMATION)
    )

    assert result == SpecialRuleResult(answer, leasable, "Special-rule reason.")
    instructions = client.generate.await_args.kwargs["instructions"]
    schema = json.loads(instructions.rsplit("```json\n", 1)[1].removesuffix("```"))
    assert set(schema["properties"]) == {"answer", "leasable", "details"}


@pytest.mark.parametrize(
    "answer,leasable",
    [
        (YES, UNKNOWN),
        (NO, YES),
        (NO, NO),
        (UNKNOWN, YES),
        (UNKNOWN, NO),
    ],
)
def test_special_rules_reject_contradictory_results(answer, leasable):
    client = AsyncMock()
    client.config = LiteLLMConfig(
        base_url="https://gateway.example/v1",
        models=("client-default",),
    )
    client.generate.return_value.text = json.dumps(
        {
            "answer": answer.value,
            "leasable": leasable.value,
            "details": "Contradictory result.",
        }
    )

    with pytest.raises(ValueError, match="invalid criterion response"):
        asyncio.run(
            criteria.SpecialRulesCriterion(client).evaluate(
                request(), PRODUCT_INFORMATION
            )
        )


def test_criterion_overrides_apply_only_to_one_call():
    client = AsyncMock()
    client.config = LiteLLMConfig(
        base_url="https://gateway.example/v1",
        models=("client-default",),
        temperature=0.5,
    )
    client.generate.return_value.text = '{"answer": "NO", "details": "A rack."}'
    criterion = criteria.ExplicitlyNotLeasableAccessoryTypeCriterion(client)
    override = client.config.with_overrides(
        models=("other-primary", "other-backup"),
        temperature=0.1,
        max_tokens=200,
        timeout_seconds=15,
    )

    asyncio.run(criterion.evaluate(request(), PRODUCT_INFORMATION, config=override))
    asyncio.run(criterion.evaluate(request(), PRODUCT_INFORMATION))

    assert client.generate.await_args_list[0].kwargs["config"] is override
    default_config = client.generate.await_args_list[1].kwargs["config"]
    assert default_config.models == criteria.DEFAULT_MODELS
    assert default_config.temperature == 0.5
    assert client.config.models == ("client-default",)
    assert client.config.temperature == 0.5
