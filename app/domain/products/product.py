from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID, uuid4


class ProductType(StrEnum):
    ACCESSORY = "ACCESSORY"
    BIKE = "BIKE"


@dataclass(frozen=True, kw_only=True)
class ProductInput:
    product_type: ProductType
    brand: str
    model: str
    year: int | None = None
    size: str | None = None
    color: str | None = None
    price: Decimal | None = None
    category: str | None = None


@dataclass(frozen=True, kw_only=True)
class ProductOrigin:
    """Identity of the submitted product in its source system."""

    source: str
    external_ref: str

    def __post_init__(self) -> None:
        if not self.source.strip() or not self.external_ref.strip():
            raise ValueError("Product origin requires source and external_ref")


@dataclass(frozen=True, kw_only=True)
class Product(ProductInput):
    """One received product entry with its own domain identity.

    A new instance receives a new id even when its origin matches an earlier
    product. That makes repeated submissions detectable without merging them.
    """

    origin: ProductOrigin
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def __post_init__(self) -> None:
        if self.created_at.tzinfo is None or self.created_at.utcoffset() is None:
            raise ValueError("Product created_at must include a timezone")
