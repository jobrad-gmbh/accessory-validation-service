import asyncio
import json
from unittest.mock import AsyncMock

import pytest

from app.adapters.llm import LiteLLMConfig, LLMModelSettings
from app.domain.criterion import CriterionResult
from app.domain.validations.accessories.leasability import criteria
from app.tests.test_leasability import PRODUCT_INFORMATION, request


@pytest.mark.parametrize("is_bawu", [False, True])
@pytest.mark.parametrize(
    "criterion_class",
    [
        criteria.ExplicitlyLeasableAccessoryTypeCriterion,
        criteria.ExplicitlyNotLeasableAccessoryTypeCriterion,
        criteria.FunctionalUnitWithBicycleCriterion,
        criteria.SpecialRulesCriterion,
    ],
)
def test_criteria_select_variant_prompts_and_keep_response_contracts(
    criterion_class, is_bawu
):
    client = AsyncMock()
    client.config = LiteLLMConfig(
        base_url="https://gateway.example/v1", models=("default",)
    )
    response = {"answer": "YES", "details": "Confirmed installation."}
    client.generate.return_value.text = json.dumps(response)
    settings = LLMModelSettings(models=("bw-test-model",))
    submitted = request(is_bawu)
    result = asyncio.run(
        criterion_class(client, is_bawu=is_bawu).evaluate(
            submitted,
            PRODUCT_INFORMATION,
            settings=settings,
            validation_id="accessory_leasability",
        )
    )
    assert isinstance(result, CriterionResult)
    assert result.criterion_id == criterion_class.id
    spec = client.generate.await_args.args[0]
    prompt_directory = (
        criteria.BAWU_PROMPTS if is_bawu else criteria.BAWU_PROMPTS.parent
    )
    expected_prompt = (
        (prompt_directory / f"{criterion_class.id}.md").read_text().strip()
    )
    assert spec.instructions.startswith(expected_prompt + "\n\n# Output\n\n")
    assert "Always answer in English" in spec.instructions
    assert spec.config.models == ("bw-test-model",)
    assert spec.description == criterion_class.id
    assert spec.validation_id == "accessory_leasability"
    assert spec.product_id == submitted.product.id
    assert "Return exactly one JSON object" in spec.instructions


@pytest.mark.parametrize(
    "criterion_class",
    [
        criteria.ExplicitlyNotLeasableAccessoryTypeCriterion,
        criteria.ExplicitlyLeasableAccessoryTypeCriterion,
        criteria.FunctionalUnitWithBicycleCriterion,
        criteria.SpecialRulesCriterion,
    ],
)
def test_bawu_retains_prompt_structure(criterion_class):
    standard_path = criteria.BAWU_PROMPTS.parent / f"{criterion_class.id}.md"
    bw_path = criteria.BAWU_PROMPTS / f"{criterion_class.id}.md"
    standard_headings = [
        line for line in standard_path.read_text().splitlines() if line.startswith("# ")
    ]
    bw_text = bw_path.read_text()
    assert [
        line for line in bw_text.splitlines() if line.startswith("# ")
    ] == standard_headings
    assert "# Land BW differences" not in bw_text
    assert "# BW " not in bw_text
    assert "Land BW 2.0" in bw_text


@pytest.mark.parametrize("is_bawu", [False, True])
def test_strategy_selects_prompts_for_every_check_and_forwards_settings(is_bawu):
    from app.domain.validation_results import ValidationStatus
    from app.domain.validations.accessories.leasability.strategies import (
        bawu_leasability_strategy,
        standard_leasability_strategy,
    )

    client = AsyncMock()
    client.config = LiteLLMConfig(
        base_url="https://gateway.example/v1", models=("default",)
    )
    client.generate.return_value.text = json.dumps(
        {"answer": "UNKNOWN", "details": "No qualifying match."}
    )
    submitted = request(is_bawu)
    strategy = bawu_leasability_strategy if is_bawu else standard_leasability_strategy
    result = asyncio.run(
        strategy(
            submitted,
            client,
            PRODUCT_INFORMATION,
            {
                "functional_unit_with_bicycle": LLMModelSettings(
                    models=("functional-test",)
                )
            },
            validation_id="accessory_leasability",
        )
    )

    expected_order = [
        "explicitly_not_leasable_type",
        "explicitly_leasable_type",
        "special_rules",
        "technical_bicycle_component",
    ]
    if not is_bawu:
        expected_order.append("stvzo_equipment")
    expected_order.extend(["functional_unit_with_bicycle", "permanently_mounted"])
    assert result.status is ValidationStatus.REJECTED
    assert [
        outcome.criterion_id for outcome in result.criterion_results
    ] == expected_order
    assert client.generate.await_count == len(expected_order)

    variant_criteria = {
        "explicitly_not_leasable_type",
        "explicitly_leasable_type",
        "special_rules",
        "functional_unit_with_bicycle",
    }
    for criterion_id, call in zip(
        expected_order, client.generate.await_args_list, strict=True
    ):
        prompt_directory = (
            criteria.BAWU_PROMPTS
            if is_bawu and criterion_id in variant_criteria
            else criteria.BAWU_PROMPTS.parent
        )
        expected_prompt = (prompt_directory / f"{criterion_id}.md").read_text().strip()
        spec = call.args[0]
        assert spec.instructions.startswith(expected_prompt + "\n\n# Output\n\n")
        assert spec.description == criterion_id
        assert spec.validation_id == "accessory_leasability"
        assert spec.product_id == submitted.product.id
        assert spec.config.models == (
            ("functional-test",)
            if criterion_id == "functional_unit_with_bicycle"
            else criteria.DEFAULT_MODELS
        )


@pytest.mark.parametrize(
    "accessory,policy_text",
    [
        ("Folding lock", "folding locks"),
        ("Chain lock", "chain locks"),
        ("U-lock", "u-locks"),
        ("Frame lock with plug-in chain", "frame-lock-and"),
        ("Battery light", "battery-powered lighting"),
        ("Display upgrade mount", "display-upgrade mounts"),
        ("Hub gears", "hub gears"),
        ("Bicycle lock mount", "lock mounts"),
    ],
)
def test_bawu_lfz_exclusion_stops_before_approval_fallbacks(accessory, policy_text):
    from dataclasses import replace
    from app.domain.validations.accessories.leasability.strategies import (
        bawu_leasability_strategy,
    )
    from app.domain.validation_results import ValidationStatus

    client = AsyncMock()
    client.config = LiteLLMConfig(
        base_url="https://gateway.example/v1", models=("test",)
    )
    client.generate.side_effect = [
        type(
            "Response",
            (),
            {
                "text": json.dumps(
                    {
                        "answer": "YES",
                        "details": "The LFZ Land BW column excludes this type.",
                    }
                )
            },
        )(),
        type(
            "Response",
            (),
            {
                "text": json.dumps(
                    {
                        "answer": "NO",
                        "details": "The LFZ exclusion applies even when fixed.",
                    }
                )
            },
        )(),
    ]
    submitted = request(True)
    submitted = replace(submitted, product=replace(submitted.product, model=accessory))
    result = asyncio.run(
        bawu_leasability_strategy(submitted, client, PRODUCT_INFORMATION)
    )
    assert result.status is ValidationStatus.REJECTED
    assert [r.criterion_id for r in result.criterion_results] == [
        "explicitly_not_leasable_type",
        "special_rules",
    ]
    assert client.generate.await_count == 2
    for call in client.generate.await_args_list:
        assert policy_text in call.args[0].instructions.lower()
        assert "locks of every type" not in call.args[0].instructions


def test_bawu_standalone_frame_lock_can_use_the_lfz_exception():
    from dataclasses import replace
    from decimal import Decimal
    from app.domain.validations.accessories.leasability.strategies import (
        bawu_leasability_strategy,
    )
    from app.domain.validation_results import ValidationStatus

    client = AsyncMock()
    client.config = LiteLLMConfig(
        base_url="https://gateway.example/v1", models=("test",)
    )
    responses = [
        {
            "answer": "NO",
            "details": "A standalone frame lock is not an excluded lock type.",
        },
        {"answer": "YES", "details": "A fixed frame lock matches the LFZ exception."},
        {"answer": "YES", "details": "The fixed frame lock costs 49 EUR."},
    ]
    client.generate.side_effect = [
        type("Response", (), {"text": json.dumps(response)})() for response in responses
    ]
    submitted = request(True)
    submitted = replace(
        submitted,
        product=replace(
            submitted.product, model="Frame lock sold alone", price=Decimal("49.00")
        ),
    )
    result = asyncio.run(
        bawu_leasability_strategy(submitted, client, PRODUCT_INFORMATION)
    )

    assert result.status is ValidationStatus.PASSED
    assert [r.criterion_id for r in result.criterion_results] == [
        "explicitly_not_leasable_type",
        "explicitly_leasable_type",
        "special_rules",
    ]
    for call in client.generate.await_args_list:
        spec = call.args[0]
        assert "frame lock sold alone" in spec.instructions.lower()
        assert "locks of every type" not in spec.instructions
        assert json.loads(spec.prompt)["price_eur"] == "49.00"
