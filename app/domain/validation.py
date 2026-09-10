"""Business context and results of accessory validation."""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel

from .accessory import Accessory
from .leasability.result import LeasabilityResult


class ValidationContext(BaseModel):
    """Context that can affect leasability, price, and other checks."""

    region: str
    is_bawu_order: bool


class PriceCheckOutcome(str, Enum):
    VALID = "valid"
    INVALID = "invalid"
    REQUIRES_REVIEW = "requires_review"




class AccessoryValidationResult(BaseModel):
    """Record of a validation run, with separate results for each check.

    A missing result means the check was not performed, never that it passed.
    No combined pass/fail policy is assumed for the independent checks.
    """

    id: str
    accessory: Accessory
    context: ValidationContext
    created_at: datetime
    leasability: LeasabilityResult | None = None
    price: PriceCheckResult | None = None
