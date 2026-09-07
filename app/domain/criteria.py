"""Business criteria and their results, independent of evaluation tools."""

from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING, Protocol

from pydantic import BaseModel, ConfigDict

from .accessory import Product, ProductInformation

if TYPE_CHECKING:
    from .validation import ValidationContext


class CriterionRef(BaseModel):
    """Immutable reference to a specific criterion version."""

    model_config = ConfigDict(frozen=True)

    id: str
    version: str


class CriterionDefinition(BaseModel):
    """Business meaning of a criterion, separate from evaluator instructions."""

    ref: CriterionRef
    name: str
    description: str


class CriterionOutcome(str, Enum):
    """Whether a condition holds; uncertainty is distinct from a negative result."""

    SATISFIED = "satisfied"
    NOT_SATISFIED = "not_satisfied"
    UNDETERMINED = "undetermined"


class CriterionEvaluation(BaseModel):
    """Result and evaluator provenance for one criterion.

    Unevaluated criteria have no result. Technical failures are handled by the
    application rather than represented as a business outcome here.
    """

    criterion: CriterionRef
    outcome: CriterionOutcome
    explanation: str
    evaluator_id: str
    evaluator_version: str


class CriterionEvaluator(Protocol):
    """Evaluator bound to one criterion definition, using any implementation."""

    @property
    def definition(self) -> CriterionDefinition: ...

    async def evaluate(
        self,
        accessory: Accessory,
        context: ValidationContext,
        information: AccessoryInformation | None = None,
    ) -> CriterionEvaluation:
        """Evaluate the condition; propagate technical failures to the caller."""
        ...
