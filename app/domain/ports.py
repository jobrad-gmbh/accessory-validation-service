from abc import ABC, abstractmethod
from typing import List, Any, Callable

from .entities import Bike


class BikeRepository(ABC):
    """Port for bike persistence operations."""

    @abstractmethod
    async def get_all(self) -> List[Bike]:
        """Get all bikes."""
        pass

    @abstractmethod
    async def get_by_id(self, bike_id: int) -> Bike | None:
        """Get a bike by ID."""
        pass

    @abstractmethod
    async def create(self, bike: Bike) -> Bike:
        """Create a new bike."""
        pass

    @abstractmethod
    async def update(self, bike_id: int, bike: Bike) -> Bike | None:
        """Update an existing bike."""
        pass

    @abstractmethod
    async def delete(self, bike_id: int) -> bool:
        """Delete a bike. Returns True if deleted, False if not found."""
        pass


class MessagePublisher(ABC):
    """Port for publishing messages."""

    @abstractmethod
    async def publish(self, topic: str, message: dict[str, Any]) -> None:
        """Publish a message to a topic."""
        pass


class MessageConsumer(ABC):
    """Port for consuming messages."""

    @abstractmethod
    async def consume(
        self, topic: str, handler: Callable[[dict[str, Any]], None]
    ) -> None:
        """Consume messages from a topic."""
        pass
