from random import Random

from app.domain.validation.request import ValidationRequest
from app.shared.decision_strategies.answers import CriterionAnswer, CriterionResult


class SpecialRulesCriterion:
    """Apply accessory-specific rules; currently returns a random test answer."""

    id = "special_rules"

    def __init__(self, randomizer: Random | None = None) -> None:
        self._randomizer = randomizer or Random()

    async def evaluate(self, request: ValidationRequest) -> CriterionResult:
        answer = self._randomizer.choice(tuple(CriterionAnswer))
        return CriterionResult(
            answer,
            f"RANDOM_{self.id.upper()}_{answer.value}",
            f"Random test answer for {self.id}: {answer.value}.",
            {"random_test_decision": True},
        )
