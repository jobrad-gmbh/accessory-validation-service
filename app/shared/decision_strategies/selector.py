from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Generic, TypeVar

from app.shared.decision_strategies.errors import StrategySelectionError
from app.shared.decision_strategies.nodes import DecisionStrategy

InputT = TypeVar("InputT")


@dataclass(frozen=True)
class StrategySelectionRule(Generic[InputT]):
    strategy: DecisionStrategy
    priority: int
    matches: Callable[[InputT], bool]


class PriorityStrategySelector(Generic[InputT]):
    def __init__(
        self,
        rules: Sequence[StrategySelectionRule[InputT]],
        default: DecisionStrategy | None = None,
    ) -> None:
        self._rules = tuple(rules)
        self._default = default

    def select(self, input_data: InputT) -> DecisionStrategy:
        matches = [rule for rule in self._rules if rule.matches(input_data)]
        if not matches:
            if self._default is None:
                raise StrategySelectionError("No applicable strategy and no default configured")
            return self._default
        highest_priority = max(rule.priority for rule in matches)
        winners = [rule for rule in matches if rule.priority == highest_priority]
        if len(winners) != 1:
            raise StrategySelectionError("Multiple strategies have the highest priority")
        return winners[0].strategy
