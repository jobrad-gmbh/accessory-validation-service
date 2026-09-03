from app.domain.entities import ClassificationContext
from app.domain.ports import LLMPort
from app.domain.rules.base import ClassificationRule


class RuleResolver:
    """Selects a rule implementation for a classification context."""

    def __init__(self, llm: LLMPort) -> None:
        self._llm = llm

    def resolve(
        self,
        rule_name: str,
        context: ClassificationContext,
    ) -> ClassificationRule:
        raise NotImplementedError("Rule resolution is not implemented yet")
