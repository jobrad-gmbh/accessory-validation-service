from decimal import Decimal

from pydantic import BaseModel, Field

from app.domain.products import Product, ProductOrigin, ProductType
from app.domain.validation import ValidationContext
from app.domain.validation.request import ValidationRequest


class AccessoryOrigin(BaseModel):
    """Reference to the accessory record in its origin system."""

    external_ref: str
    source: str


class AccessoryInput(BaseModel):
    """Complete submitted payload, including validation context and origin."""

    brand: str
    model: str
    price: Decimal = Field(ge=0, allow_inf_nan=False)
    context: ValidationContext
    origin: AccessoryOrigin
    color: str | None = None
    size: str | None = None

    def to_domain(self) -> ValidationRequest:
        return ValidationRequest(
            product=Product(
                product_type=ProductType.ACCESSORY,
                brand=self.brand,
                model=self.model,
                price=self.price,
                color=self.color,
                size=self.size,
                origin=ProductOrigin(
                    source=self.origin.source,
                    external_ref=self.origin.external_ref,
                ),
            ),
            context=self.context,
        )


class ErrorWebResponse(BaseModel):
    """Error detail schema."""

    code: str
    message: str
    details: str | None = None
    translations: dict[str, str] | None = None


class ErrorListWebResponse(BaseModel):
    """Error response schema."""

    errors: list[ErrorWebResponse]
