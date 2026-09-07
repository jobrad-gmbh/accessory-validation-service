"""Accessory details and information used during validation."""

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class Accessory(BaseModel):
    """Accessory details used during validation."""

    brand: str
    model: str
    price: Decimal = Field(ge=0, allow_inf_nan=False)
    color: str | None = None
    size: str | None = None


class AccessoryInformation(BaseModel):
    """Researched description and consulted sources, separate from user input."""

    description: str
    sources: tuple[str, ...]
    retrieved_at: datetime
