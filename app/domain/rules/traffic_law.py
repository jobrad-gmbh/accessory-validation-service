from app.domain.ports import LLMPort
from app.domain.rules.base import ClassificationRule


class TrafficLawRule(ClassificationRule):
    name = "traffic_law_required"

    def __init__(self, llm: LLMPort) -> None:
        self._llm = llm

    async def evaluate(self, description: str) -> bool:
        raise NotImplementedError("Traffic-law rule is not implemented yet")
