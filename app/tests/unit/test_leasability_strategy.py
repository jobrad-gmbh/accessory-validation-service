import asyncio

import pytest
from pydantic import ValidationError

from app.domain.accessory import Accessory
from app.domain.criteria import (
    CriterionDefinition,
    CriterionEvaluation,
    CriterionOutcome,
    CriterionRef,
)
from app.domain.leasability.result import LeasabilityOutcome
from app.domain.leasability.strategies.exclusion_first import (
    AcceptancePath,
    ExclusionFirstStrategy,
    ExclusionFirstStrategyConfig,
)
from app.domain.validation import ValidationContext


def reference(name, version="1"):
    return CriterionRef(id=name, version=version)


def config(fallback="not_leasable"):
    return ExclusionFirstStrategyConfig(
        id="test_strategy",
        version="1",
        exclusions=(reference("excluded_1"), reference("excluded_2")),
        acceptance_paths=(
            AcceptancePath(id="combined", all_of=(reference("a"), reference("b"))),
            AcceptancePath(id="alternative", all_of=(reference("c"),)),
        ),
        fallback=fallback,
    )


def accessory(model="Rack"):
    return Accessory(brand="Example", model=model, price="149.90")


def context():
    return ValidationContext(region="DE", is_bawu_order=True)


class RecordingEvaluator:
    def __init__(self, criterion, answers, calls):
        self.definition = CriterionDefinition(
            ref=criterion, name=criterion.id, description="Fictional test criterion."
        )
        self.answers = answers
        self.calls = calls

    async def evaluate(self, accessory, context, information=None):
        criterion = self.definition.ref
        self.calls.append((criterion, accessory, context, information))
        assert criterion.id in self.answers, "Unexpected evaluation after stopping"
        outcome = self.answers[criterion.id]
        if isinstance(outcome, Exception):
            raise outcome
        return CriterionEvaluation(
            criterion=criterion,
            outcome=outcome,
            explanation="Result supplied by the test evaluator.",
            evaluator_id="test_evaluator",
            evaluator_version="1",
        )


def evaluators_for(policy, answers, calls):
    required = set(policy.exclusions)
    for path in policy.acceptance_paths:
        required.update(path.all_of)
    return {
        criterion: RecordingEvaluator(criterion, answers, calls)
        for criterion in required
    }


def run_strategy(policy, answers):
    calls = []
    strategy = ExclusionFirstStrategy(policy, evaluators_for(policy, answers, calls))
    result = asyncio.run(strategy.evaluate(accessory(), context()))
    return result, calls


@pytest.mark.parametrize(
    ("answers", "expected"),
    [
        ({"excluded_1": "satisfied"}, LeasabilityOutcome.NOT_LEASABLE),
        (
            {"excluded_1": "not_satisfied", "excluded_2": "satisfied"},
            LeasabilityOutcome.NOT_LEASABLE,
        ),
        ({"excluded_1": "undetermined"}, LeasabilityOutcome.REQUIRES_REVIEW),
        (
            {"excluded_1": "not_satisfied", "excluded_2": "undetermined"},
            LeasabilityOutcome.REQUIRES_REVIEW,
        ),
        (
            {
                "excluded_1": "not_satisfied",
                "excluded_2": "not_satisfied",
                "a": "satisfied",
                "b": "satisfied",
            },
            LeasabilityOutcome.LEASABLE,
        ),
        (
            {
                "excluded_1": "not_satisfied",
                "excluded_2": "not_satisfied",
                "a": "not_satisfied",
                "c": "satisfied",
            },
            LeasabilityOutcome.LEASABLE,
        ),
        (
            {
                "excluded_1": "not_satisfied",
                "excluded_2": "not_satisfied",
                "a": "undetermined",
            },
            LeasabilityOutcome.REQUIRES_REVIEW,
        ),
        (
            {
                "excluded_1": "not_satisfied",
                "excluded_2": "not_satisfied",
                "a": "satisfied",
                "b": "undetermined",
            },
            LeasabilityOutcome.REQUIRES_REVIEW,
        ),
        (
            {
                "excluded_1": "not_satisfied",
                "excluded_2": "not_satisfied",
                "a": "satisfied",
                "b": "not_satisfied",
                "c": "satisfied",
            },
            LeasabilityOutcome.LEASABLE,
        ),
    ],
)
def test_strategy_executes_rules_in_order_and_stops(answers, expected):
    result, calls = run_strategy(config(), answers)
    assert result.outcome == expected
    assert [call[0].id for call in calls] == list(answers)
    assert [evaluation.criterion.id for evaluation in result.evaluations] == list(
        answers
    )
    assert result.strategy.id == "test_strategy"
    assert result.strategy.version == "1"


@pytest.mark.parametrize("fallback", ["not_leasable", "requires_review"])
def test_exhausted_acceptance_paths_use_explicit_fallback(fallback):
    result, _ = run_strategy(
        config(fallback),
        {
            "excluded_1": "not_satisfied",
            "excluded_2": "not_satisfied",
            "a": "not_satisfied",
            "c": "not_satisfied",
        },
    )
    assert result.outcome == LeasabilityOutcome(fallback)


def test_strategy_with_no_conditions_uses_fallback():
    policy = ExclusionFirstStrategyConfig(
        id="empty",
        version="1",
        exclusions=(),
        acceptance_paths=(),
        fallback="requires_review",
    )
    result, calls = run_strategy(policy, {})
    assert result.outcome == LeasabilityOutcome.REQUIRES_REVIEW
    assert result.evaluations == ()
    assert calls == []


def test_shared_criterion_is_evaluated_once_within_a_run():
    policy = ExclusionFirstStrategyConfig(
        id="shared",
        version="1",
        exclusions=(),
        acceptance_paths=(
            AcceptancePath(id="first", all_of=(reference("a"), reference("b"))),
            AcceptancePath(id="second", all_of=(reference("a"), reference("c"))),
        ),
        fallback="not_leasable",
    )
    result, calls = run_strategy(
        policy, {"a": "satisfied", "b": "not_satisfied", "c": "satisfied"}
    )
    assert result.outcome == LeasabilityOutcome.LEASABLE
    assert [call[0].id for call in calls] == ["a", "b", "c"]


def test_missing_evaluator_is_rejected_before_execution():
    with pytest.raises(ValueError, match="Missing evaluator"):
        ExclusionFirstStrategy(config(), {})


def test_evaluator_for_a_different_version_is_rejected():
    policy = config()
    evaluators = evaluators_for(policy, {}, [])
    evaluators[reference("excluded_1")] = RecordingEvaluator(
        reference("excluded_1", "0"), {}, []
    )
    with pytest.raises(ValueError, match="definition must match"):
        ExclusionFirstStrategy(policy, evaluators)


def test_mismatched_result_reference_is_rejected():
    class WrongVersionEvaluator(RecordingEvaluator):
        async def evaluate(self, accessory, context, information=None):
            result = await super().evaluate(accessory, context, information)
            return result.model_copy(update={"criterion": reference("excluded_1", "0")})

    policy = config()
    calls = []
    answers = {"excluded_1": "not_satisfied"}
    evaluators = evaluators_for(policy, answers, calls)
    evaluators[reference("excluded_1")] = WrongVersionEvaluator(
        reference("excluded_1"), answers, calls
    )
    strategy = ExclusionFirstStrategy(policy, evaluators)
    with pytest.raises(ValueError, match="requested criterion version"):
        asyncio.run(strategy.evaluate(accessory(), context()))
    assert len(calls) == 1


def test_technical_failure_is_not_converted_to_a_business_outcome():
    with pytest.raises(RuntimeError, match="provider unavailable"):
        run_strategy(config(), {"excluded_1": RuntimeError("provider unavailable")})


def test_concurrent_runs_do_not_reuse_another_accessorys_results():
    class ModelEvaluator(RecordingEvaluator):
        async def evaluate(self, accessory, context, information=None):
            await asyncio.sleep(0)
            self.calls.append((self.definition.ref, accessory, context, information))
            return CriterionEvaluation(
                criterion=self.definition.ref,
                outcome=(
                    CriterionOutcome.SATISFIED
                    if accessory.model == "Excluded"
                    else CriterionOutcome.NOT_SATISFIED
                ),
                explanation="Fictional deterministic check.",
                evaluator_id="model_check",
                evaluator_version="1",
            )

    policy = ExclusionFirstStrategyConfig(
        id="concurrent",
        version="1",
        exclusions=(reference("excluded"),),
        acceptance_paths=(),
        fallback="requires_review",
    )
    calls = []
    strategy = ExclusionFirstStrategy(
        policy,
        {reference("excluded"): ModelEvaluator(reference("excluded"), {}, calls)},
    )

    async def evaluate_both():
        return await asyncio.gather(
            strategy.evaluate(accessory("Excluded"), context()),
            strategy.evaluate(accessory("Other"), context()),
        )

    first, second = asyncio.run(evaluate_both())
    assert first.outcome == LeasabilityOutcome.NOT_LEASABLE
    assert second.outcome == LeasabilityOutcome.REQUIRES_REVIEW
    assert first.evaluations[0].outcome != second.evaluations[0].outcome
    assert len(calls) == 2


def test_empty_acceptance_path_cannot_accidentally_accept():
    with pytest.raises(ValidationError):
        AcceptancePath(id="empty", all_of=())


@pytest.mark.parametrize("fallback", ["leasable", "unknown", None])
def test_invalid_fallback_is_rejected(fallback):
    with pytest.raises(ValidationError):
        config(fallback)


def test_fallback_must_be_explicit():
    with pytest.raises(ValidationError):
        ExclusionFirstStrategyConfig.model_validate(
            config().model_dump(exclude={"fallback"})
        )
