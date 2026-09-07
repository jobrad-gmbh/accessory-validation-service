from collections.abc import Sequence
from typing import Generic, TypeVar

from app.shared.decision_strategies.answers import CriterionAnswer
from app.shared.decision_strategies.contracts import Criterion
from app.shared.decision_strategies.errors import StrategyConfigurationError, StrategyExecutionError
from app.shared.decision_strategies.nodes import CriterionNode, DecisionStrategy
from app.shared.decision_strategies.results import StrategyEvaluation, TraceStep

InputT = TypeVar("InputT")


class DecisionTreeEvaluator(Generic[InputT]):
    def __init__(self, criteria: Sequence[Criterion[InputT]]) -> None:
        self._criteria: dict[str, Criterion[InputT]] = {}
        for criterion in criteria:
            if not criterion.id.strip() or criterion.id in self._criteria:
                raise StrategyConfigurationError("Criterion ids must be non-empty and unique")
            self._criteria[criterion.id] = criterion

    def validate_strategy(self, strategy: DecisionStrategy) -> None:
        for node in strategy.nodes.values():
            if isinstance(node, CriterionNode) and node.criterion_id not in self._criteria:
                raise StrategyConfigurationError(f"Unregistered criterion: {node.criterion_id}")

    async def evaluate(self, strategy: DecisionStrategy, input_data: InputT) -> StrategyEvaluation:
        self.validate_strategy(strategy)
        node = strategy.nodes[strategy.entry_node_id]
        trace: list[TraceStep] = []
        while isinstance(node, CriterionNode):
            criterion = self._criteria[node.criterion_id]
            try:
                result = await criterion.evaluate(input_data)
                if not isinstance(result.answer, CriterionAnswer):
                    raise TypeError("Criterion returned an unsupported answer")
            except Exception as exc:
                raise StrategyExecutionError(
                    f"Criterion {node.criterion_id} failed at node {node.id}"
                ) from exc
            trace.append(TraceStep(node.id, node.criterion_id, result))
            node = strategy.nodes[node.next_node_id(result.answer)]
        decision_node = node
        return StrategyEvaluation(
            strategy.id,
            strategy.version,
            decision_node.id,
            decision_node.decision,
            decision_node.reason_code,
            decision_node.details,
            tuple(trace),
        )
