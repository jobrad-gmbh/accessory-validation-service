from typing import Protocol, TypeVar

from app.shared.decision_strategies.answers import CriterionResult
from app.shared.decision_strategies.nodes import DecisionStrategy

InputT = TypeVar("InputT", contravariant=True)


class Criterion(Protocol[InputT]):
    @property
    def id(self) -> str: ...

    async def evaluate(self, input_data: InputT) -> CriterionResult: ...


class StrategySelector(Protocol[InputT]):
    def select(self, input_data: InputT) -> DecisionStrategy: ...
