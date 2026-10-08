import asyncio
import json
from unittest.mock import AsyncMock

import pytest

from app.adapters.llm import LiteLLMConfig, LLMModelSettings
from app.domain.criterion import CriterionResult
from app.domain.validations.accessories.leasability import bawu_criteria, criteria
from app.tests.test_leasability import PRODUCT_INFORMATION, request


@pytest.mark.parametrize("criterion_class", [
    bawu_criteria.BawuExplicitlyLeasableAccessoryTypeCriterion,
    bawu_criteria.BawuExplicitlyNotLeasableAccessoryTypeCriterion,
    bawu_criteria.BawuFunctionalUnitWithBicycleCriterion,
    bawu_criteria.BawuSpecialRulesCriterion,
])
def test_bawu_criteria_use_separate_prompts_and_response_contracts(criterion_class):
    client = AsyncMock()
    client.config = LiteLLMConfig(base_url="https://gateway.example/v1", models=("default",))
    response = {"answer": "YES", "details": "Confirmed installation."}
    client.generate.return_value.text = json.dumps(response)
    settings = LLMModelSettings(models=("bw-test-model",))
    result = asyncio.run(criterion_class(client).evaluate(request(True), PRODUCT_INFORMATION, settings=settings))
    assert isinstance(result, CriterionResult)
    assert result.criterion_id == criterion_class.id
    spec = client.generate.await_args.args[0]
    assert "Land BW 2.0" in spec.instructions
    assert "Always answer in English" in spec.instructions
    assert spec.config.models == ("bw-test-model",)
    assert spec.description == criterion_class.id
    assert "Return exactly one JSON object" in spec.instructions


@pytest.mark.parametrize("standard_class,bw_class", [
    (criteria.ExplicitlyNotLeasableAccessoryTypeCriterion, bawu_criteria.BawuExplicitlyNotLeasableAccessoryTypeCriterion),
    (criteria.ExplicitlyLeasableAccessoryTypeCriterion, bawu_criteria.BawuExplicitlyLeasableAccessoryTypeCriterion),
    (criteria.FunctionalUnitWithBicycleCriterion, bawu_criteria.BawuFunctionalUnitWithBicycleCriterion),
    (criteria.SpecialRulesCriterion, bawu_criteria.BawuSpecialRulesCriterion),
])
def test_bawu_retains_criterion_contract_and_prompt_structure(standard_class, bw_class):
    assert issubclass(bw_class, standard_class)
    assert bw_class.id == standard_class.id
    standard_path = criteria.Path(criteria.__file__).with_name("prompts") / f"{standard_class.id}.md"
    bw_path = bawu_criteria.PROMPTS / f"{bw_class.id}.md"
    standard_headings = [line for line in standard_path.read_text().splitlines() if line.startswith("# ")]
    bw_text = bw_path.read_text()
    assert [line for line in bw_text.splitlines() if line.startswith("# ")] == standard_headings
    assert "# Land BW differences" not in bw_text
    assert "# BW " not in bw_text
    assert "Land BW 2.0" in bw_text


@pytest.mark.parametrize("accessory,policy_text", [
    ("Folding lock", "folding locks"),
    ("Chain lock", "chain locks"),
    ("U-lock", "u-locks"),
    ("Frame lock with plug-in chain", "frame-lock-and"),
    ("Battery light", "battery-powered lighting"),
    ("Display upgrade mount", "display-upgrade mounts"),
    ("Hub gears", "hub gears"),
    ("Bicycle lock mount", "lock mounts"),
])
def test_bawu_lfz_exclusion_stops_before_approval_fallbacks(accessory, policy_text):
    from dataclasses import replace
    from app.domain.validations.accessories.leasability.strategies import bawu_leasability_strategy
    from app.domain.validation_results import ValidationStatus

    client = AsyncMock()
    client.config = LiteLLMConfig(base_url="https://gateway.example/v1", models=("test",))
    client.generate.side_effect = [
        type("Response", (), {"text": json.dumps({"answer": "YES", "details": "The LFZ Land BW column excludes this type."})})(),
        type("Response", (), {"text": json.dumps({"answer": "NO", "details": "The LFZ exclusion applies even when fixed."})})(),
    ]
    submitted = request(True)
    submitted = replace(submitted, product=replace(submitted.product, model=accessory))
    result = asyncio.run(bawu_leasability_strategy(submitted, client, PRODUCT_INFORMATION))
    assert result.status is ValidationStatus.REJECTED
    assert [r.criterion_id for r in result.criterion_results] == ["explicitly_not_leasable_type", "special_rules"]
    assert client.generate.await_count == 2
    for call in client.generate.await_args_list:
        assert policy_text in call.args[0].instructions.lower()
        assert "locks of every type" not in call.args[0].instructions


def test_bawu_standalone_frame_lock_can_use_the_lfz_exception():
    from dataclasses import replace
    from decimal import Decimal
    from app.domain.validations.accessories.leasability.strategies import bawu_leasability_strategy
    from app.domain.validation_results import ValidationStatus

    client = AsyncMock()
    client.config = LiteLLMConfig(base_url="https://gateway.example/v1", models=("test",))
    responses = [
        {"answer": "NO", "details": "A standalone frame lock is not an excluded lock type."},
        {"answer": "YES", "details": "A fixed frame lock matches the LFZ exception."},
        {"answer": "YES", "details": "The fixed frame lock costs 49 EUR."},
    ]
    client.generate.side_effect = [
        type("Response", (), {"text": json.dumps(response)})()
        for response in responses
    ]
    submitted = request(True)
    submitted = replace(submitted, product=replace(
        submitted.product, model="Frame lock sold alone", price=Decimal("49.00")
    ))
    result = asyncio.run(bawu_leasability_strategy(submitted, client, PRODUCT_INFORMATION))

    assert result.status is ValidationStatus.PASSED
    assert [r.criterion_id for r in result.criterion_results] == [
        "explicitly_not_leasable_type", "explicitly_leasable_type", "special_rules"
    ]
    for call in client.generate.await_args_list:
        spec = call.args[0]
        assert "frame lock sold alone" in spec.instructions.lower()
        assert "locks of every type" not in spec.instructions
        assert json.loads(spec.prompt)["price_eur"] == "49.00"
