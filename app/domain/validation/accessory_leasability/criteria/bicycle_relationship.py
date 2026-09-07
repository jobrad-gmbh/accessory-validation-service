from random import Random

from app.domain.validation.request import ValidationRequest
from app.shared.decision_strategies.answers import CriterionAnswer, CriterionResult


class TechnicalBicycleComponentCriterion:
    id = "technical_bicycle_component"

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


class StvzoEquipmentCriterion:
    id = "stvzo_equipment"

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


class FunctionalUnitWithBicycleCriterion:
    id = "functional_unit_with_bicycle"

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


class InstallableOnBicycleCriterion:
    id = "installable_on_bicycle"

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
