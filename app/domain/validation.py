from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Protocol, final

from app.domain.product import Product, ProductContext
from app.domain.validation_results import (
    ValidationExecution,
    ValidationResult,
)


@dataclass(frozen=True)
class ValidationRequest:
    """Submitted product and business context shared by the configured validations.

    Resolved information is obtained by the validation or criterion that needs it;
    it must not replace the submitted product in this request.
    """

    product: Product
    context: ProductContext = field(default_factory=ProductContext)


class Validation(Protocol):
    """An independent business check with a stable id."""

    @property
    def id(self) -> str: ...

    async def validate(self, request: ValidationRequest) -> ValidationExecution: ...


class SimpleValidation(ABC):
    """Build an execution around a validation's business result."""

    id: str

    @final
    async def validate(self, request: ValidationRequest) -> ValidationExecution:
        result = await self.evaluate_result(request)
        return ValidationExecution(
            product=request.product,
            validation_id=self.id,
            result=result,
        )

    @abstractmethod
    async def evaluate_result(self, request: ValidationRequest) -> ValidationResult: ...
