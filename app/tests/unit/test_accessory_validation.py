import asyncio
from datetime import datetime, timezone

from app.adapters.web.schemas import AccessoryInput
from app.domain.accessory import Accessory, AccessoryInformation
from app.domain.criteria import CriterionDefinition, CriterionEvaluation, CriterionRef
from app.domain.leasability.result import (
    LeasabilityOutcome,
    LeasabilityResult,
    LeasabilityStrategyRef,
)
from app.domain.leasability.strategies.base import LeasabilityStrategy
from app.domain.leasability.strategies.exclusion_first import (
    ExclusionFirstStrategy,
    ExclusionFirstStrategyConfig,
)
from app.domain.validation import (
    AccessoryValidationResult,
    PriceCheckOutcome,
    PriceCheckResult,
    ValidationContext,
)


def test_validation_record_retains_independent_results_and_research():
    submitted = AccessoryInput.model_validate(
        {
            "brand": "Example",
            "model": "Rack",
            "price": "149.90",
            "context": {"region": "DE", "is_bawu_order": True},
            "origin": {"external_id": "external-123", "source": "odoo"},
        }
    )
    accessory = Accessory.model_validate(
        submitted.model_dump(exclude={"context", "origin"})
    )
    now = datetime.now(timezone.utc)
    information = AccessoryInformation(
        description="Description used by the evaluator.",
        sources=("https://example.com/rack",),
        retrieved_at=now,
    )
    criterion = CriterionRef(id="excluded", version="2")

    class DeterministicEvaluator:
        definition = CriterionDefinition(
            ref=criterion, name="Test exclusion", description="Fictional test rule."
        )

        async def evaluate(self, actual_accessory, context, actual_information=None):
            assert actual_accessory == accessory
            assert context == submitted.context
            assert actual_information == information
            return CriterionEvaluation(
                criterion=criterion,
                outcome="satisfied",
                explanation="Test exclusion applies.",
                evaluator_id="deterministic",
                evaluator_version="3",
            )

    policy = ExclusionFirstStrategyConfig(
        id="regional",
        version="4",
        exclusions=(criterion,),
        acceptance_paths=(),
        fallback="requires_review",
    )
    strategy = ExclusionFirstStrategy(policy, {criterion: DeterministicEvaluator()})
    leasability = asyncio.run(
        strategy.evaluate(accessory, submitted.context, information)
    )
    record = AccessoryValidationResult(
        id="validation-123",
        accessory=accessory,
        context=submitted.context,
        created_at=now,
        leasability=leasability,
        price=PriceCheckResult(
            outcome=PriceCheckOutcome.VALID, explanation="Price check passed."
        ),
    )
    restored = AccessoryValidationResult.model_validate_json(record.model_dump_json())
    assert restored == record
    assert restored.leasability.outcome == LeasabilityOutcome.NOT_LEASABLE
    assert restored.price.outcome == PriceCheckOutcome.VALID
    assert restored.leasability.strategy.version == "4"
    assert restored.leasability.evaluations[0].criterion.version == "2"
    assert restored.leasability.evaluations[0].evaluator_version == "3"
    assert restored.leasability.information.sources == information.sources
    assert restored.context.is_bawu_order is True
    assert submitted.origin.external_id == "external-123"


def test_independent_strategy_implementation_can_supply_a_check_result():
    class ManualReviewStrategy:
        ref = LeasabilityStrategyRef(id="manual_review", version="1")

        async def evaluate(self, accessory, context, information=None):
            return LeasabilityResult(
                outcome=LeasabilityOutcome.REQUIRES_REVIEW,
                explanation="Test strategy requests manual review.",
                strategy=self.ref,
                evaluations=(),
                information=information,
            )

    strategy: LeasabilityStrategy = ManualReviewStrategy()
    accessory = Accessory(brand="Example", model="Rack", price="149.90")
    context = ValidationContext(region="DE", is_bawu_order=False)
    result = asyncio.run(strategy.evaluate(accessory, context))
    record = AccessoryValidationResult(
        id="validation-456",
        accessory=accessory,
        context=context,
        created_at=datetime.now(timezone.utc),
        leasability=result,
    )
    restored = AccessoryValidationResult.model_validate_json(record.model_dump_json())
    assert restored.price is None
    assert restored.leasability.outcome == LeasabilityOutcome.REQUIRES_REVIEW
    assert restored.leasability.information is None
    assert restored.leasability.evaluations == ()
