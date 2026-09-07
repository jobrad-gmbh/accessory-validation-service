from typing import List, Any

from app.domain.entities import Bike
from app.domain.ports import BikeRepository, MessagePublisher


from app.config.logging import get_logger

logger = get_logger(__name__)


class BikeInventoryService:
    """Implementation of bike business logic."""

    def __init__(
        self,
        bike_repository: BikeRepository | None = None,
        message_publisher: MessagePublisher | None = None,
    ):
        self._bike_repository = bike_repository
        self._message_publisher = message_publisher

    async def list_bikes(self) -> List[Bike]:
        """List all bikes."""
        if not self._bike_repository:
            logger.error("Bike repository is not configured.")
            return []
        return await self._bike_repository.get_all()

    async def get_bike(self, bike_id: int) -> Bike | None:
        """Get a specific bike."""
        if not self._bike_repository:
            logger.error("Bike repository is not configured.")
            return None
        return await self._bike_repository.get_by_id(bike_id)

    async def create_bike(self, bike: Bike) -> Bike:
        """Create a new bike and publish creation event."""
        if not self._bike_repository:
            logger.error("Bike repository is not configured.")
            raise ValueError("Bike repository is not configured.")
        created_bike = await self._bike_repository.create(bike)

        # Publish bike creation event (non-blocking, failures won't affect bike creation)
        if self._message_publisher and created_bike.id is not None:
            try:
                event_message: dict[str, Any] = {
                    "event_type": "bike_created",
                    "bike_id": created_bike.id,
                    "brand": created_bike.brand,
                    "model": created_bike.model,
                    "bike_type": created_bike.bike_type.value,
                }
                await self._message_publisher.publish("bike-events", event_message)
            except Exception as e:
                # Log the error but don't fail the bike creation
                logger.error(
                    f"Failed to publish bike creation event for bike {created_bike.id}: {e}"
                )

        return created_bike

    async def update_bike(self, bike_id: int, bike: Bike) -> Bike | None:
        """Update an existing bike."""
        if not self._bike_repository:
            logger.error("Bike repository is not configured.")
            return None
        return await self._bike_repository.update(bike_id, bike)

    async def delete_bike(self, bike_id: int) -> bool:
        """Delete a bike."""
        if not self._bike_repository:
            logger.error("Bike repository is not configured.")
            return False
        return await self._bike_repository.delete(bike_id)
