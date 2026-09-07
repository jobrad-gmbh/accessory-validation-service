from pydantic import BaseModel

from app.domain.entities import BikeType


class BikeCreateWebRequest(BaseModel):
    """Request schema for creating a bike."""

    brand: str
    model: str
    bike_type: BikeType


class BikeUpdateWebRequest(BaseModel):
    """Request schema for updating a bike."""

    brand: str
    model: str
    bike_type: BikeType


class BikeWebResponse(BaseModel):
    """Response schema for a bike."""

    id: int
    brand: str
    model: str
    bike_type: BikeType


class BikeListWebResponse(BaseModel):
    """Response schema for bike list."""

    data: list[BikeWebResponse]


class ErrorWebResponse(BaseModel):
    """Error detail schema."""

    code: str
    message: str
    details: str | None = None
    translations: dict[str, str] | None = None


class ErrorListWebResponse(BaseModel):
    """Error response schema."""

    errors: list[ErrorWebResponse]
