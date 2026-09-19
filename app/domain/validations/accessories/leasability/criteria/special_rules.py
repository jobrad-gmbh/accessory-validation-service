from random import Random

from app.domain.criterion import CriterionAnswer, CriterionResult
from app.domain.validation import (
    ValidationRequest,
)


class SpecialRulesCriterion:
    """Apply accessory-specific rules; currently returns a random test answer."""

    id = "special_rules"

    def __init__(self, randomizer: Random | None = None) -> None:
        self._randomizer = randomizer or Random()

    async def evaluate(self, request: ValidationRequest) -> CriterionResult:
        answer = self._randomizer.choice(tuple(CriterionAnswer))
        return CriterionResult(
            answer,
            f"Random test answer for {self.id}: {answer.value}.",
        )
