import asyncio
import json
from unittest.mock import AsyncMock

import pytest

from app.adapters.llm import LiteLLMConfig, LLMModelSettings
from app.domain.criterion import CriterionResult, SpecialRuleResult
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
    special = criterion_class is bawu_criteria.BawuSpecialRulesCriterion
    if special:
        response["leasable"] = "YES"
    client.generate.return_value.text = json.dumps(response)
    settings = LLMModelSettings(models=("bw-test-model",))
    result = asyncio.run(criterion_class(client).evaluate(request(True), PRODUCT_INFORMATION, settings=settings))
    assert isinstance(result, SpecialRuleResult if special else CriterionResult)
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


@pytest.mark.parametrize("lock", ["Frame lock", "Folding lock", "Chain lock", "U-lock", "ABUS One Key Solution"])
def test_bawu_lock_exclusion_stops_before_approval_fallbacks(lock):
    from dataclasses import replace
    from app.domain.validations.accessories.leasability.strategies import bawu_leasability_strategy
    from app.domain.validation_results import ValidationStatus

    client = AsyncMock()
    client.config = LiteLLMConfig(base_url="https://gateway.example/v1", models=("test",))
    client.generate.side_effect = [
        type("Response", (), {"text": json.dumps({"answer": "YES", "details": "All lock types are excluded for BW."})})(),
        type("Response", (), {"text": json.dumps({"answer": "YES", "leasable": "NO", "details": "Locks are excluded even when fixed."})})(),
    ]
    submitted = request(True)
    submitted = replace(submitted, product=replace(submitted.product, model=lock))
    result = asyncio.run(bawu_leasability_strategy(submitted, client, PRODUCT_INFORMATION))
    assert result.status is ValidationStatus.REJECTED
    assert [r.criterion_id for r in result.criterion_results] == ["explicitly_not_leasable_type", "special_rules"]
    assert client.generate.await_count == 2
    for call in client.generate.await_args_list:
        assert "locks of every type" in call.args[0].instructions
