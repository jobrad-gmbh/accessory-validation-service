from dataclasses import dataclass, field

from app.domain.products.product import Product


@dataclass(frozen=True)
class ValidationContext:
    """Typed business context; fields are added when their meaning is defined."""


@dataclass(frozen=True)
class ValidationRequest:
    """Submitted product and business context shared by the configured validations.

    Resolved information is obtained by the validation or criterion that needs it;
    it must not replace the submitted product in this request.
    """

    product: Product
    context: ValidationContext = field(default_factory=ValidationContext)
