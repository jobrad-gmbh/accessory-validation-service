from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from types import MappingProxyType

from app.shared.decision_strategies.answers import CriterionAnswer
from app.shared.decision_strategies.errors import StrategyConfigurationError


class StrategyDecision(StrEnum):
    ACCEPT = "ACCEPT"
    REJECT = "REJECT"
    UNDETERMINED = "UNDETERMINED"


@dataclass(frozen=True)
class CriterionNode:
    id: str
    criterion_id: str
    on_yes: str
    on_no: str
    on_unknown: str

    def next_node_id(self, answer: CriterionAnswer) -> str:
        return {
            CriterionAnswer.YES: self.on_yes,
            CriterionAnswer.NO: self.on_no,
            CriterionAnswer.UNKNOWN: self.on_unknown,
        }[answer]


@dataclass(frozen=True)
class DecisionNode:
    id: str
    decision: StrategyDecision
    reason_code: str
    details: str


StrategyNode = CriterionNode | DecisionNode


@dataclass(frozen=True)
class DecisionStrategy:
    id: str
    version: str
    entry_node_id: str
    nodes: Mapping[str, StrategyNode]

    def __post_init__(self) -> None:
        object.__setattr__(self, "nodes", MappingProxyType(dict(self.nodes)))
        self._validate_definition()

    def _validate_definition(self) -> None:
        if not self.id.strip() or not self.version.strip():
            raise StrategyConfigurationError("Strategies require a non-empty id and version")
        if self.entry_node_id not in self.nodes:
            raise StrategyConfigurationError("Strategy entry node does not exist")
        for node_id, node in self.nodes.items():
            if not isinstance(node, (CriterionNode, DecisionNode)):
                raise StrategyConfigurationError(f"Unsupported node type at {node_id}")
            if not node_id.strip() or node_id != node.id:
                raise StrategyConfigurationError("Node keys must match non-empty node ids")
            if isinstance(node, CriterionNode):
                if not node.criterion_id.strip():
                    raise StrategyConfigurationError(f"Missing criterion id at node {node_id}")
                for target in (node.on_yes, node.on_no, node.on_unknown):
                    if target not in self.nodes:
                        raise StrategyConfigurationError(
                            f"Unknown target {target} at node {node_id}"
                        )
            elif (
                not isinstance(node.decision, StrategyDecision)
                or not node.reason_code.strip()
                or not node.details.strip()
            ):
                raise StrategyConfigurationError(f"Invalid decision at node {node_id}")

        active: set[str] = set()
        visited: set[str] = set()
        stack = [(self.entry_node_id, False)]
        while stack:
            node_id, exiting = stack.pop()
            if exiting:
                active.remove(node_id)
                visited.add(node_id)
                continue
            if node_id in active:
                raise StrategyConfigurationError(f"Strategy contains a cycle at {node_id}")
            if node_id in visited:
                continue
            active.add(node_id)
            stack.append((node_id, True))
            node = self.nodes[node_id]
            if isinstance(node, CriterionNode):
                stack.extend(
                    (target, False) for target in (node.on_unknown, node.on_no, node.on_yes)
                )
        if visited != set(self.nodes):
            raise StrategyConfigurationError("Strategy contains unreachable nodes")
