"""Business criterion results and their possible answers."""

from dataclasses import dataclass
from enum import StrEnum


class CriterionAnswer(StrEnum):
    YES = "YES"
    NO = "NO"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class CriterionResult:
    answer: CriterionAnswer
    details: str


@dataclass(frozen=True)
class SpecialRuleResult:
    answer: CriterionAnswer
    leasable: CriterionAnswer
    details: str
