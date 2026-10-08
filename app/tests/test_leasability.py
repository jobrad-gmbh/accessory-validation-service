import asyncio
import json
from unittest.mock import AsyncMock

import pytest
from pydantic import BaseModel, ValidationError

from app.adapters.llm import LiteLLMConfig, LLMModelSettings, LLMResponseError
from app.domain.criterion import CriterionAnswer, CriterionResult
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
    async def evaluate(
        self, submitted, product_information, *, settings=None, validation_id=None
    ):
        assert validation_id == "accessory_leasability"
        assert product_information is PRODUCT_INFORMATION
        calls.append(self.id)
        configured = answers.get(
            self.id, UNKNOWN if self.id == "special_rules" else default
        )
        if isinstance(configured, CriterionResult):
            assert configured.criterion_id == self.id
            return configured
        return CriterionResult(configured, "Deterministic criterion answer.", self.id)

    for criterion in (
        strategies.ExplicitlyNotLeasableAccessoryTypeCriterion,
        strategies.ExplicitlyLeasableAccessoryTypeCriterion,
        strategies.SpecialRulesCriterion,
        strategies.TechnicalBicycleComponentCriterion,
        strategies.StvzoEquipmentCriterion,
        strategies.FunctionalUnitWithBicycleCriterion,
        strategies.PermanentlyMountedCriterion,
        strategies.BawuExplicitlyLeasableAccessoryTypeCriterion,
        strategies.BawuExplicitlyNotLeasableAccessoryTypeCriterion,
        strategies.BawuFunctionalUnitWithBicycleCriterion,
        strategies.BawuSpecialRulesCriterion,
    ):
        monkeypatch.setattr(criterion, "evaluate", evaluate)


@pytest.mark.parametrize("is_bawu", [False, True])
def test_validation_retrieves_product_information_once(monkeypatch, is_bawu):
    calls = []
    criteria_with_answers(monkeypatch, {ORDER[0]: YES}, calls)
    information_service = AsyncMock(spec=AccessoryProductInformationService)
    information_service.retrieve.return_value = PRODUCT_INFORMATION
    submitted = request(is_bawu)

    execution = asyncio.run(
        AccessoryLeasabilityValidation(
            AsyncMock(), information_service
        ).validate(submitted)
    )

    information_service.retrieve.assert_awaited_once_with(
        submitted.product,
        product_id=submitted.product.id,
        validation_id="accessory_leasability",
    )
    assert execution.result.product_information is PRODUCT_INFORMATION
    assert calls == [ORDER[0], "special_rules"]


@pytest.mark.parametrize("is_bawu", [False, True])
@pytest.mark.parametrize("excluded", [False, True])
@pytest.mark.parametrize(
    "special",
    [
        CriterionResult(YES, "A leasable special rule matched.", "special_rules"),
        CriterionResult(NO, "A non-leasable special rule matched.", "special_rules"),
        CriterionResult(UNKNOWN, "No special rule matched.", "special_rules"),
        CriterionResult(UNKNOWN, "Eligibility could not be determined.", "special_rules"),
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

    passed = special.answer is YES if special.answer is not UNKNOWN else not excluded
    assert execution.result.status is (
        ValidationStatus.PASSED if passed else ValidationStatus.REJECTED
    )
    assert execution.product is submitted.product
    assert execution.validation_id == "accessory_leasability"
    assert calls == ([ORDER[0]] if excluded else list(ORDER[:2])) + ["special_rules"]
    assert execution.result.details == (
        special.details
        if special.answer is not UNKNOWN
        else "Deterministic criterion answer."
    )


@pytest.mark.parametrize("is_bawu", [False, True])
@pytest.mark.parametrize("default", [NO, UNKNOWN])
@pytest.mark.parametrize("answer", [YES, NO])
def test_special_rules_decide_without_an_explicit_type_match(
    monkeypatch, is_bawu, default, answer
):
    calls = []
    special = CriterionResult(answer, "Special rule decides.", "special_rules")
    criteria_with_answers(
        monkeypatch,
        {"special_rules": special, "technical_bicycle_component": YES},
        calls,
        default,
    )

    execution = asyncio.run(validation().validate(request(is_bawu)))

    assert execution.result.status is (
        ValidationStatus.PASSED if answer is YES else ValidationStatus.REJECTED
    )
    assert execution.result.details == special.details
    assert calls == [*ORDER[:2], "special_rules"]
    assert execution.result.criterion_results[-1] == special


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
    applicable.insert(2, "special_rules")
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
    if passed:
        assert execution.result.details == "Deterministic criterion answer."
    else:
        assert execution.result.details == (
            "The accessory did not match an explicitly leasable type and was not "
            "identified as a technical component, "
            + ("" if is_bawu else "StVZO-related equipment, ")
            + "a functional unit with the bicycle, or a bike-mounted item."
        )
        assert execution.result.criterion_results[-1].details == (
            "Deterministic criterion answer."
        )


def test_decisive_criterion_provides_validation_details(monkeypatch):
    calls = []
    decisive = CriterionResult(YES, "The rack is a technical bicycle component.", "technical_bicycle_component")
    criteria_with_answers(
        monkeypatch,
        {"technical_bicycle_component": decisive},
        calls,
    )

    execution = asyncio.run(validation().validate(request()))

    assert execution.result.status is ValidationStatus.PASSED
    assert execution.result.details == decisive.details


def test_criterion_results_list_every_evaluated_criterion_in_order(monkeypatch):
    calls = []
    special = CriterionResult(UNKNOWN, "No special rule matched.", "special_rules")
    criteria_with_answers(
        monkeypatch, {ORDER[1]: YES, "special_rules": special}, calls
    )

    execution = asyncio.run(validation().validate(request()))

    assert execution.result.criterion_results == (
        CriterionResult(NO, "Deterministic criterion answer.", criterion_id=ORDER[0]),
        CriterionResult(YES, "Deterministic criterion answer.", criterion_id=ORDER[1]),
        CriterionResult(UNKNOWN, special.details, criterion_id="special_rules"),
    )


@pytest.mark.parametrize("is_bawu", [False, True])
def test_criterion_results_match_short_circuited_criteria(monkeypatch, is_bawu):
    calls = []
    criteria_with_answers(monkeypatch, {"functional_unit_with_bicycle": YES}, calls)

    execution = asyncio.run(validation().validate(request(is_bawu)))

    assert [result.criterion_id for result in execution.result.criterion_results] == calls
    assert execution.result.criterion_results[-1].answer is YES


def test_special_rule_result_keeps_eligibility_answer(monkeypatch):
    calls = []
    criteria_with_answers(
        monkeypatch,
        {ORDER[0]: YES, "special_rules": CriterionResult(NO, "Override.", "special_rules")},
        calls,
    )

    execution = asyncio.run(validation().validate(request()))

    assert execution.result.criterion_results[-1] == CriterionResult(
        NO, "Override.", criterion_id="special_rules"
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
    service = ProductValidationService([validation()], AsyncMock())
    with pytest.raises(
        ValidationExecutionError, match="Validation accessory_leasability failed"
    ) as exc:
        asyncio.run(service.validate(request()))
    assert exc.value.__cause__ is failure
    assert exc.value.validation_id == "accessory_leasability"
    assert "RuntimeError: Provider unavailable" in str(exc.value)
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

    submitted = request()
    result = asyncio.run(
        criteria.ExplicitlyNotLeasableAccessoryTypeCriterion(client).evaluate(
            submitted, PRODUCT_INFORMATION, validation_id="accessory_leasability"
        )
    )

    assert result == CriterionResult(answer, "Classification reason.", "explicitly_not_leasable_type")
    assert client.generate.await_args.args[0].product_id == submitted.product.id
    assert client.generate.await_args.args[0].validation_id == "accessory_leasability"
    product_payload = json.loads(client.generate.await_args.args[0].prompt)
    assert product_payload["brand"] == "Example"
    assert product_payload["model"] == "Rack"
    assert product_payload["product_information"] == {
        "summary": PRODUCT_INFORMATION.summary,
        "sources": [],
    }
    instructions = client.generate.await_args.args[0].instructions
    assert "# Explicitly not-leasable accessory types" in instructions
    assert "Bicycle trailers" in instructions
    assert "Return exactly one JSON object" in instructions
    assert "No json fences" in instructions
    schema = json.loads(instructions.rsplit("```json\n", 1)[1].removesuffix("```"))
    assert set(schema["properties"]) == {"answer", "details"}
    assert client.generate.await_args.args[0].description == "explicitly_not_leasable_type"
    assert client.generate.await_args.args[0].config.models == criteria.DEFAULT_MODELS


def test_explicitly_leasable_type_accepts_a_single_json_code_fence():
    client = AsyncMock()
    client.config = LiteLLMConfig(
        base_url="https://gateway.example/v1",
        models=("client-default",),
    )
    client.generate.return_value.text = (
        '```json\n{"answer": "NO", "details": "No listed type matches."}\n```'
    )

    result = asyncio.run(
        criteria.ExplicitlyLeasableAccessoryTypeCriterion(client).evaluate(
            request(), PRODUCT_INFORMATION
        )
    )

    assert result == CriterionResult(
        NO, "No listed type matches.", "explicitly_leasable_type"
    )


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
    client.generate.return_value.model = "criterion-model"

    with pytest.raises(LLMResponseError, match="invalid criterion response") as error:
        asyncio.run(
            criteria.ExplicitlyNotLeasableAccessoryTypeCriterion(client).evaluate(
                request(), PRODUCT_INFORMATION
            )
        )
    assert "Model 'criterion-model'" in str(error.value)
    assert "during 'explicitly_not_leasable_type'" in str(error.value)
    assert isinstance(error.value.__cause__, ValidationError)


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

    assert result == CriterionResult(answer, "Classification reason.", "explicitly_leasable_type")
    instructions = client.generate.await_args.args[0].instructions
    assert "# Explicitly leasable accessory types" in instructions
    assert "Bike lock" in instructions
    assert client.generate.await_args.args[0].config.models == criteria.DEFAULT_MODELS


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

    assert result == CriterionResult(YES, "Classification reason.", criterion_class.id)
    assert prompt_heading in client.generate.await_args.args[0].instructions
    assert client.generate.await_args.args[0].config.models == criteria.DEFAULT_MODELS


@pytest.mark.parametrize("is_bawu", [False, True])
@pytest.mark.parametrize("answer", list(CriterionAnswer))
def test_special_rules_use_single_eligibility_answer(is_bawu, answer):
    client = AsyncMock()
    client.config = LiteLLMConfig(
        base_url="https://gateway.example/v1",
        models=("client-default",),
    )
    client.generate.return_value.text = json.dumps(
        {
            "answer": answer.value,
            "details": "Special-rule reason.",
        }
    )

    criterion_class = (
        strategies.BawuSpecialRulesCriterion if is_bawu else criteria.SpecialRulesCriterion
    )
    result = asyncio.run(
        criterion_class(client).evaluate(request(is_bawu), PRODUCT_INFORMATION)
    )

    assert result == CriterionResult(answer, "Special-rule reason.", "special_rules")
    instructions = client.generate.await_args.args[0].instructions
    assert 'Is this accessory leasable according to the matched rule?' in instructions
    assert "when no special rule applies" in instructions
    schema = json.loads(instructions.rsplit("```json\n", 1)[1].removesuffix("```"))
    assert set(schema["properties"]) == {"answer", "details"}


@pytest.mark.parametrize("is_bawu", [False, True])
@pytest.mark.parametrize("price", ["0", "29.00", "49.00", "150.00", None])
def test_special_rules_receive_submitted_euro_price(is_bawu, price):
    from dataclasses import replace
    from decimal import Decimal

    client = AsyncMock()
    client.config = LiteLLMConfig(base_url="https://gateway.example/v1", models=("test",))
    client.generate.return_value.text = json.dumps({
        "answer": "UNKNOWN", "details": "No special rule matched."
    })
    submitted = request(is_bawu)
    submitted = replace(submitted, product=replace(
        submitted.product, price=Decimal(price) if price is not None else None
    ))
    criterion_class = (
        strategies.BawuSpecialRulesCriterion if is_bawu else criteria.SpecialRulesCriterion
    )

    asyncio.run(criterion_class(client).evaluate(submitted, PRODUCT_INFORMATION))

    spec = client.generate.await_args.args[0]
    assert json.loads(spec.prompt)["price_eur"] == price
    assert "submitted `price_eur`" in spec.instructions
    assert "150 EUR" in spec.instructions
    assert "49 EUR" in spec.instructions
    assert "29 EUR" in spec.instructions


@pytest.mark.parametrize("is_bawu", [False, True])
def test_unknown_battery_special_rule_continues_to_technical_component(is_bawu):
    client = AsyncMock()
    client.config = LiteLLMConfig(
        base_url="https://gateway.example/v1",
        models=("client-default",),
    )
    responses = [
        {"answer": "NO", "details": "No explicit exclusion."},
        {"answer": "NO", "details": "No explicit approval."},
        {"answer": "UNKNOWN", "details": "The e-bike battery's role is unclear."},
        {"answer": "YES", "details": "A technical bicycle component."},
    ]
    client.generate.side_effect = [
        type("Response", (), {"text": json.dumps(response)})()
        for response in responses
    ]
    strategy = (
        strategies.bawu_leasability_strategy if is_bawu
        else strategies.standard_leasability_strategy
    )

    result = asyncio.run(strategy(request(is_bawu), client, PRODUCT_INFORMATION))

    assert result.status is ValidationStatus.PASSED
    assert [r.criterion_id for r in result.criterion_results] == [
        *ORDER[:2], "special_rules", "technical_bicycle_component"
    ]
    assert result.criterion_results[2].answer is UNKNOWN
    assert client.generate.await_count == 4


def test_criterion_overrides_apply_only_to_one_call():
    client = AsyncMock()
    client.config = LiteLLMConfig(
        base_url="https://gateway.example/v1",
        models=("client-default",),
        temperature=0.5,
    )
    client.generate.return_value.text = '{"answer": "NO", "details": "A rack."}'
    criterion = criteria.ExplicitlyNotLeasableAccessoryTypeCriterion(client)
    settings = LLMModelSettings(
        models=("other-primary", "other-backup"),
        temperature=0.1,
        max_tokens=200,
        timeout_seconds=15,
    )

    asyncio.run(criterion.evaluate(request(), PRODUCT_INFORMATION, settings=settings))
    asyncio.run(criterion.evaluate(request(), PRODUCT_INFORMATION))

    overridden = client.generate.await_args_list[0].args[0].config
    assert overridden.models == ("other-primary", "other-backup")
    assert overridden.temperature == 0.1
    assert overridden.max_tokens == 200
    assert overridden.timeout_seconds == 15
    assert overridden.base_url == client.config.base_url
    default_config = client.generate.await_args_list[1].args[0].config
    assert default_config.models == criteria.DEFAULT_MODELS
    assert default_config.temperature == 0.5
    assert client.config.models == ("client-default",)
    assert client.config.temperature == 0.5
