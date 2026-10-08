from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import final

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


class Validation(ABC):
    """A business check that wraps its result in a validation execution."""

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
