from enum import Enum
from pydantic import BaseModel


class BikeType(str, Enum):
    GRAVEL = "GRAVEL"
    ROAD = "ROAD"
    MOUNTAIN = "MOUNTAIN"
    CITY = "CITY"
    PEDELEC = "PEDELEC"


class Bike(BaseModel):
    id: int | None = None
    brand: str
    model: str
    bike_type: BikeType

    def __repr__(self) -> str:
        return f"Bike(id={self.id!r}, brand={self.brand!r}, model={self.model!r}, bike_type={self.bike_type!r})"
