from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import Enum as SQLEnum

from app.domain.entities import BikeType


class BaseSQLModel(DeclarativeBase):
    pass


class BikeSQLModel(BaseSQLModel):
    __tablename__ = "bike"

    id: Mapped[int] = mapped_column(primary_key=True)
    brand: Mapped[str] = mapped_column()
    model: Mapped[str] = mapped_column()
    bike_type: Mapped[BikeType] = mapped_column(SQLEnum(BikeType))

    def __repr__(self) -> str:
        return f"BikeModel(id={self.id!r}, brand={self.brand!r}, model={self.model!r}, bike_type={self.bike_type!r})"
