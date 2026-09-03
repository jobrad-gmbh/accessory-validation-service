from abc import ABC, abstractmethod


class DecisionStrategy(ABC):
    name: str
    required_rules: tuple[str, ...]

    @abstractmethod
    def try_decide(self, results: dict[str, bool]) -> bool | None:
        raise NotImplementedError

    @abstractmethod
    def final_decision(self, results: dict[str, bool]) -> bool:
        raise NotImplementedError
