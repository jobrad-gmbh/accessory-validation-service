from typing import List
from sqlalchemy import create_engine, Engine
from sqlalchemy.orm import Session
from app.config.settings import settings

from app.domain.entities import Bike
from app.domain.ports import BikeRepository
from .sql_models import BikeSQLModel

_default_engine = create_engine(settings.SQLALCHEMY_DATABASE_URI)


class SQLAlchemyBikeRepository(BikeRepository):
    """SQLAlchemy implementation of the bike repository."""

    def __init__(self, engine: Engine | None = None):
        """Initialize repository with optional engine for dependency injection."""
        self.engine = engine or _default_engine

    async def get_all(self) -> List[Bike]:
        """Get all bikes."""
        with Session(self.engine) as session:
            bike_sql_models = session.query(BikeSQLModel).all()
            return [
                self._sql_to_domain_model(bike_model) for bike_model in bike_sql_models
            ]

    async def get_by_id(self, bike_id: int) -> Bike | None:
        with Session(self.engine) as session:
            bike_sql_model = session.get(BikeSQLModel, bike_id)
            if bike_sql_model:
                return self._sql_to_domain_model(bike_sql_model)
            return None

    async def create(self, bike: Bike) -> Bike:
        with Session(self.engine) as session:
            bike_sql_model = BikeSQLModel(
                brand=bike.brand, model=bike.model, bike_type=bike.bike_type
            )
            session.add(bike_sql_model)
            session.commit()
            session.refresh(bike_sql_model)
            return self._sql_to_domain_model(bike_sql_model)

    async def update(self, bike_id: int, bike: Bike) -> Bike | None:
        with Session(self.engine) as session:
            bike_sql_model = session.query(BikeSQLModel).get(bike_id)
            if bike_sql_model:
                bike_sql_model.brand = bike.brand
                bike_sql_model.model = bike.model
                bike_sql_model.bike_type = bike.bike_type
                session.add(bike_sql_model)
                session.commit()
                session.refresh(bike_sql_model)
                return self._sql_to_domain_model(bike_sql_model)
            return None

    async def delete(self, bike_id: int) -> bool:
        with Session(self.engine) as session:
            bike_sql_model = session.query(BikeSQLModel).get(bike_id)
            if bike_sql_model:
                session.delete(bike_sql_model)
                session.commit()
                return True
            return False

    def _sql_to_domain_model(self, bike_model: BikeSQLModel) -> Bike:
        return Bike(
            id=bike_model.id,
            brand=bike_model.brand,
            model=bike_model.model,
            bike_type=bike_model.bike_type,
        )
