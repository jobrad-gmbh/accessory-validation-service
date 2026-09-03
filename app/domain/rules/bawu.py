from app.domain.ports import LLMPort
from app.domain.rules.base import ClassificationRule


class BawuPermanentlyAttachedRule(ClassificationRule):
    """Placeholder for the BaWü variant of permanent-attachment evaluation."""

    name = "permanently_attached"

    def __init__(self, llm: LLMPort) -> None:
        self._llm = llm

    async def evaluate(self, description: str) -> bool:
        raise NotImplementedError("BaWü rule variant is not implemented yet")
