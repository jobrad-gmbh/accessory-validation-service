from dataclasses import dataclass

from app.shared.decision_strategies.answers import CriterionResult
from app.shared.decision_strategies.nodes import StrategyDecision


@dataclass(frozen=True)
class TraceStep:
    node_id: str
    criterion_id: str
    result: CriterionResult


@dataclass(frozen=True)
class StrategyEvaluation:
    strategy_id: str
    strategy_version: str
    decision_node_id: str
    decision: StrategyDecision
    reason_code: str
    details: str
    trace: tuple[TraceStep, ...]
