from abc import ABC, abstractmethod


class AccessoryResearchPort(ABC):
    """Port for collecting a normalized description of an accessory."""

    @abstractmethod
    async def research(self, accessory_name: str) -> str:
        raise NotImplementedError


class LLMPort(ABC):
    """Port used by research and rule implementations."""

    @abstractmethod
    async def ask_boolean(self, question: str, description: str) -> bool:
        raise NotImplementedError
