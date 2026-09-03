from app.domain.ports import LLMPort
from app.domain.rules.base import ClassificationRule


class ExcludedCategoryRule(ClassificationRule):
    name = "explicitly_excluded"

    def __init__(self, llm: LLMPort) -> None:
        self._llm = llm

    async def evaluate(self, description: str) -> bool:
        raise NotImplementedError("Excluded-category rule is not implemented yet")
