from random import Random

from app.domain.validation.request import ValidationRequest
from app.shared.decision_strategies.answers import CriterionAnswer, CriterionResult


class ExplicitlyNotLeasableAccessoryTypeCriterion:
    id = "explicitly_not_leasable_type"

    def __init__(self, randomizer: Random | None = None) -> None:
        self._randomizer = randomizer or Random()

    async def evaluate(self, request: ValidationRequest) -> CriterionResult:
        answer = self._randomizer.choice((CriterionAnswer.YES, CriterionAnswer.NO))
        return CriterionResult(
            answer,
            f"RANDOM_{self.id.upper()}_{answer.value}",
            f"Random test answer for {self.id}: {answer.value}.",
            {"random_test_decision": True},
        )


class ExplicitlyLeasableAccessoryTypeCriterion:
    id = "explicitly_leasable_type"

    def __init__(self, randomizer: Random | None = None) -> None:
        self._randomizer = randomizer or Random()

    async def evaluate(self, request: ValidationRequest) -> CriterionResult:
        answer = self._randomizer.choice((CriterionAnswer.YES, CriterionAnswer.NO))
        return CriterionResult(
            answer,
            f"RANDOM_{self.id.upper()}_{answer.value}",
            f"Random test answer for {self.id}: {answer.value}.",
            {"random_test_decision": True},
        )
