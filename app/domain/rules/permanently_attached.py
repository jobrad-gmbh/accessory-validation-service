from app.domain.ports import LLMPort
from app.domain.rules.base import ClassificationRule


class PermanentlyAttachedRule(ClassificationRule):
    name = "permanently_attached"

    def __init__(self, llm: LLMPort) -> None:
        self._llm = llm

    async def evaluate(self, description: str) -> bool:
        raise NotImplementedError("Permanently attached rule is not implemented yet")
