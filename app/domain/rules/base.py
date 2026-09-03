from abc import ABC, abstractmethod


class ClassificationRule(ABC):
    name: str

    @abstractmethod
    async def evaluate(self, description: str) -> bool:
        raise NotImplementedError
