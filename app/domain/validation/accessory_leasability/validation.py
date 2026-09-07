from collections.abc import Sequence

from app.domain.validation.accessory_leasability.strategy import (
    standard_leasability_strategy,
)
from app.domain.validation.request import ValidationRequest
from app.domain.validation.results import EvidenceValue, ValidationResult, ValidationStatus
from app.domain.validation.validation import StrategyBasedValidation
from app.shared.decision_strategies.contracts import Criterion
from app.shared.decision_strategies.evaluator import DecisionTreeEvaluator
from app.shared.decision_strategies.nodes import StrategyDecision
from app.shared.decision_strategies.results import StrategyEvaluation
from app.shared.decision_strategies.selector import PriorityStrategySelector


class AccessoryLeasabilityValidation(StrategyBasedValidation):
    """Apply a leasing strategy and translate its decision into a business result."""

    id = "accessory_leasability"

    def __init__(self, criteria: Sequence[Criterion[ValidationRequest]]) -> None:
        strategy = standard_leasability_strategy()
        evaluator = DecisionTreeEvaluator(criteria)
        evaluator.validate_strategy(strategy)
        super().__init__(
            PriorityStrategySelector([], default=strategy),
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
            reason_code=evaluation.reason_code,
            details=evaluation.details,
            evidence=self._business_evidence(evaluation),
        )

    @staticmethod
    def _business_evidence(evaluation: StrategyEvaluation) -> dict[str, EvidenceValue]:
        evidence: dict[str, EvidenceValue] = {}
        for step in evaluation.trace:
            evidence.update(step.result.evidence)
        return evidence
