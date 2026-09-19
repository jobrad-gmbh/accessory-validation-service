from random import Random

from app.domain.criterion import CriterionAnswer, CriterionResult
from app.domain.validation import (
    ValidationRequest,
)


class ExplicitlyNotLeasableAccessoryTypeCriterion:
    id = "explicitly_not_leasable_type"

    def __init__(self, randomizer: Random | None = None) -> None:
        self._randomizer = randomizer or Random()

    async def evaluate(self, request: ValidationRequest) -> CriterionResult:
        answer = self._randomizer.choice((CriterionAnswer.YES, CriterionAnswer.NO))
        return CriterionResult(
            answer,
            f"Random test answer for {self.id}: {answer.value}.",
        )


class ExplicitlyLeasableAccessoryTypeCriterion:
    id = "explicitly_leasable_type"

    def __init__(self, randomizer: Random | None = None) -> None:
        self._randomizer = randomizer or Random()

    async def evaluate(self, request: ValidationRequest) -> CriterionResult:
        answer = self._randomizer.choice((CriterionAnswer.YES, CriterionAnswer.NO))
        return CriterionResult(
            answer,
            f"Random test answer for {self.id}: {answer.value}.",
        )

class TechnicalBicycleComponentCriterion:
    id = "technical_bicycle_component"

    def __init__(self, randomizer: Random | None = None) -> None:
        self._randomizer = randomizer or Random()

    async def evaluate(self, request: ValidationRequest) -> CriterionResult:
        answer = self._randomizer.choice((CriterionAnswer.YES, CriterionAnswer.NO))
        return CriterionResult(
            answer,
            f"Random test answer for {self.id}: {answer.value}.",
        )


class StvzoEquipmentCriterion:
    id = "stvzo_equipment"

    def __init__(self, randomizer: Random | None = None) -> None:
        self._randomizer = randomizer or Random()

    async def evaluate(self, request: ValidationRequest) -> CriterionResult:
        answer = self._randomizer.choice((CriterionAnswer.YES, CriterionAnswer.NO))
        return CriterionResult(
            answer,
            f"Random test answer for {self.id}: {answer.value}.",
        )


class FunctionalUnitWithBicycleCriterion:
    id = "functional_unit_with_bicycle"

    def __init__(self, randomizer: Random | None = None) -> None:
        self._randomizer = randomizer or Random()

    async def evaluate(self, request: ValidationRequest) -> CriterionResult:
        answer = self._randomizer.choice((CriterionAnswer.YES, CriterionAnswer.NO))
        return CriterionResult(
            answer,
            f"Random test answer for {self.id}: {answer.value}.",
        )


class InstallableOnBicycleCriterion:
    id = "installable_on_bicycle"

    def __init__(self, randomizer: Random | None = None) -> None:
        self._randomizer = randomizer or Random()

    async def evaluate(self, request: ValidationRequest) -> CriterionResult:
        answer = self._randomizer.choice((CriterionAnswer.YES, CriterionAnswer.NO))
        return CriterionResult(
            answer,
            f"Random test answer for {self.id}: {answer.value}.",
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
