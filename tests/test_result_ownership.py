import asyncio
from random import Random

import pytest

from app.adapters.web.schemas import AccessoryInput
from app.domain.products import Product, ProductOrigin, ProductType
from app.domain.validation import (
    ProductValidationService,
    SimpleValidation,
    ValidationExecution,
    ValidationResult,
    ValidationStatus,
)
from app.domain.validation.accessory_leasability.criteria import (
    ExplicitlyLeasableAccessoryTypeCriterion,
    ExplicitlyNotLeasableAccessoryTypeCriterion,
    FunctionalUnitWithBicycleCriterion,
    InstallableOnBicycleCriterion,
    SpecialRulesCriterion,
    StvzoEquipmentCriterion,
    TechnicalBicycleComponentCriterion,
)
from app.domain.validation.accessory_leasability.strategy import (
    standard_leasability_strategy,
)
from app.domain.validation.accessory_leasability.validation import (
    AccessoryLeasabilityValidation,
)
from app.domain.validation.errors import ValidationExecutionError
from app.domain.validation.request import ValidationRequest
from app.shared.decision_strategies.answers import CriterionAnswer, CriterionResult
from app.shared.decision_strategies.evaluator import DecisionTreeEvaluator
from app.shared.decision_strategies.nodes import CriterionNode, StrategyDecision
from app.shared.decision_strategies.results import StrategyEvaluation


def product(*, external_ref: str = "ACC-42", category: str | None = None) -> Product:
    return Product(
        product_type=ProductType.ACCESSORY,
        brand="Example",
        model="Rack",
        category=category,
        origin=ProductOrigin(source="odoo", external_ref=external_ref),
    )


def validation_result():
    return ValidationResult(
        status=ValidationStatus.PASSED,
        reason_code="ALLOWED",
        details="Accessory is allowed.",
    )


def evaluation() -> StrategyEvaluation:
    return StrategyEvaluation(
        strategy_id="standard_accessory_leasability",
        strategy_version="2",
        decision_node_id="allowed",
        decision=StrategyDecision.ACCEPT,
        reason_code="ALLOWED",
        details="Accessory is allowed.",
        trace=(),
    )


def test_every_input_gets_a_new_product_id_even_with_the_same_origin():
    first = product()
    second = product()

    assert first.id != second.id
    assert first.origin == second.origin


def test_accessory_input_maps_origin_and_creates_a_new_product():
    submitted = AccessoryInput.model_validate(
        {
            "brand": "Example",
            "model": "Rack",
            "price": "49.99",
            "context": {},
            "origin": {"source": "odoo", "external_ref": "ACC-42"},
        }
    )

    first = submitted.to_domain().product
    second = submitted.to_domain().product

    assert first.id != second.id
    assert first.origin == ProductOrigin(source="odoo", external_ref="ACC-42")


def test_validation_execution_owns_its_result_and_strategy_evaluations():
    associated_product = product()
    strategy_evaluation = evaluation()

    execution = ValidationExecution(
        validation_id="accessory_leasability",
        product=associated_product,
        result=validation_result(),
        strategy_evaluations=(strategy_evaluation,),
    )

    assert execution.product is associated_product
    assert execution.result.status is ValidationStatus.PASSED
    assert execution.strategy_evaluations == (strategy_evaluation,)
    assert not hasattr(execution, "product_id")
    assert not hasattr(strategy_evaluation, "validation_result_id")


def test_simple_validation_creates_an_execution_without_strategies():
    associated_product = product()

    class AlwaysPasses(SimpleValidation):
        id = "always_passes"

        async def evaluate_result(self, request):
            return validation_result()

    execution = asyncio.run(
        AlwaysPasses().validate(ValidationRequest(product=associated_product))
    )

    assert execution.product is associated_product
    assert execution.validation_id == "always_passes"
    assert execution.strategy_evaluations == ()


def test_service_rejects_a_validation_execution_for_another_product():
    requested_product = product()
    other_product = product(external_ref="OTHER")

    class WrongProductValidation:
        id = "accessory_leasability"

        async def validate(self, request):
            return ValidationExecution(
                product=other_product,
                validation_id=self.id,
                result=validation_result(),
            )

    service = ProductValidationService([WrongProductValidation()])

    with pytest.raises(ValidationExecutionError, match="failed"):
        asyncio.run(service.validate(ValidationRequest(product=requested_product)))


def test_strategy_validation_always_captures_its_evaluation():
    associated_product = product()
    policy = standard_leasability_strategy()
    randomizer = Random(7)
    validation = AccessoryLeasabilityValidation(
        [
            ExplicitlyNotLeasableAccessoryTypeCriterion(randomizer),
            SpecialRulesCriterion(randomizer),
            ExplicitlyLeasableAccessoryTypeCriterion(randomizer),
            TechnicalBicycleComponentCriterion(randomizer),
            StvzoEquipmentCriterion(randomizer),
            FunctionalUnitWithBicycleCriterion(randomizer),
            InstallableOnBicycleCriterion(randomizer),
        ]
    )

    execution = asyncio.run(
        validation.validate(ValidationRequest(product=associated_product))
    )

    assert execution.product is associated_product
    assert execution.result.status in {
        ValidationStatus.PASSED,
        ValidationStatus.REJECTED,
    }
    assert len(execution.strategy_evaluations) == 1
    strategy_evaluation = execution.strategy_evaluations[0]
    assert strategy_evaluation.strategy_id == policy.id
    assert strategy_evaluation.strategy_version == "2"
    assert strategy_evaluation.trace[0].criterion_id == "explicitly_not_leasable_type"
    assert all(
        step.result.evidence["random_test_decision"]
        for step in strategy_evaluation.trace
    )


@pytest.mark.parametrize(
    ("answers", "expected"),
    [
        (
            {
                "explicitly_not_leasable_type": CriterionAnswer.YES,
                "special_rules": CriterionAnswer.UNKNOWN,
            },
            StrategyDecision.REJECT,
        ),
        (
            {
                "explicitly_leasable_type": CriterionAnswer.YES,
                "special_rules": CriterionAnswer.UNKNOWN,
            },
            StrategyDecision.ACCEPT,
        ),
        (
            {"technical_bicycle_component": CriterionAnswer.YES},
            StrategyDecision.ACCEPT,
        ),
        ({"stvzo_equipment": CriterionAnswer.YES}, StrategyDecision.ACCEPT),
        ({"functional_unit_with_bicycle": CriterionAnswer.YES}, StrategyDecision.ACCEPT),
        ({"installable_on_bicycle": CriterionAnswer.YES}, StrategyDecision.ACCEPT),
        ({}, StrategyDecision.REJECT),
    ],
)
def test_leasability_strategy_routes_each_business_rule(answers, expected):
    strategy = standard_leasability_strategy()

    class FixedCriterion:
        def __init__(self, criterion_id, answer):
            self.id = criterion_id
            self._answer = answer

        async def evaluate(self, request):
            return CriterionResult(
                self._answer,
                "FIXED_TEST_ANSWER",
                "Fixed answer used to verify strategy routing.",
            )

    criterion_ids = {
        node.criterion_id
        for node in strategy.nodes.values()
        if isinstance(node, CriterionNode)
    }
    criteria = [
        FixedCriterion(
            criterion_id,
            answers.get(criterion_id, CriterionAnswer.NO),
        )
        for criterion_id in criterion_ids
    ]

    evaluation = asyncio.run(
        DecisionTreeEvaluator(criteria).evaluate(
            strategy,
            ValidationRequest(product=product()),
        )
    )

    assert evaluation.decision is expected
