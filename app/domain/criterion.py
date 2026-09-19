"""Business criterion contract and its possible answers."""

from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol

from app.domain.validation import ValidationRequest


class CriterionAnswer(StrEnum):
    YES = "YES"
    NO = "NO"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class CriterionResult:
    answer: CriterionAnswer
    details: str


class Criterion(Protocol):
    @property
    def id(self) -> str: ...

    async def evaluate(self, request: ValidationRequest) -> CriterionResult: ...
