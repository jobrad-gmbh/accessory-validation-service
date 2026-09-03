from app.domain.decisions.base import DecisionStrategy
from app.domain.entities import ClassificationContext


class DecisionStrategyResolver:
    """Selects a decision strategy for a classification context."""

    def resolve(self, context: ClassificationContext) -> DecisionStrategy:
        raise NotImplementedError("Decision strategy resolution is not implemented yet")
