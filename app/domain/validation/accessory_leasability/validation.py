from collections.abc import Sequence

from app.domain.validation.accessory_leasability.strategy import (
    bawu_leasability_strategy,
    standard_leasability_strategy,
)
from app.domain.validation.request import ValidationRequest
from app.domain.validation.results import ValidationResult, ValidationStatus
from app.domain.validation.validation import StrategyBasedValidation
from app.shared.decision_strategies.contracts import Criterion
from app.shared.decision_strategies.evaluator import DecisionTreeEvaluator
from app.shared.decision_strategies.nodes import StrategyDecision
from app.shared.decision_strategies.results import StrategyEvaluation
from app.shared.decision_strategies.selector import (
    PriorityStrategySelector,
    StrategySelectionRule,
)


class AccessoryLeasabilityValidation(StrategyBasedValidation):
    """Apply a leasing strategy and translate its decision into a business result."""

    id = "accessory_leasability"

    def __init__(self, criteria: Sequence[Criterion[ValidationRequest]]) -> None:
        strategy = standard_leasability_strategy()
        bawu_strategy = bawu_leasability_strategy()
        evaluator = DecisionTreeEvaluator(criteria)
        evaluator.validate_strategy(strategy)
        evaluator.validate_strategy(bawu_strategy)
        super().__init__(
            PriorityStrategySelector(
                [
                    StrategySelectionRule(
                        strategy=bawu_strategy,
                        priority=1,
                        matches=lambda request: request.context.is_bawu_order,
                    )
                ],
                default=strategy,
            ),
            evaluator,
        )

    def result_from_strategy(self, evaluation: StrategyEvaluation) -> ValidationResult:
        status = {
            StrategyDecision.ACCEPT: ValidationStatus.PASSED,
            StrategyDecision.REJECT: ValidationStatus.REJECTED,
            StrategyDecision.UNDETERMINED: ValidationStatus.UNDETERMINED,
        }[evaluation.decision]
        return ValidationResult(
            status=status,
            details=evaluation.details,
        )
