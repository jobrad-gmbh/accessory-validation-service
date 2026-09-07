from typing import Annotated

from fastapi import Depends

from app.domain.bike_inventory_service import BikeInventoryService
{%- if 'postgresql' in values.features %}
from app.adapters.persistence.repositories import SQLAlchemyBikeRepository
{%- endif %}
{%- if 'kafka' in values.features %}
from app.adapters.messaging.kafka import KafkaMessagePublisher
{%- endif %}

from app.config.logging import get_logger
from app.config.settings import settings

logger = get_logger(__name__)


def get_bike_service() -> BikeInventoryService:
    bike_repository: BikeRepository | None = None
    {%- if 'postgresql' in values.features %}
    """Get bike use case with injected dependencies."""
    bike_repository = SQLAlchemyBikeRepository()
    {%- endif %}

    message_publisher: KafkaMessagePublisher | None = None
    {%- if 'kafka' in values.features %}
    # Configure message publisher if Kafka is available
    bootstrap_servers = settings.KAFKA_BOOTSTRAP_SERVERS

    if bootstrap_servers and bootstrap_servers.strip():
        logger.info(
            f"Kafka configured with bootstrap servers: {bootstrap_servers.strip()}"
        )
        message_publisher = KafkaMessagePublisher(bootstrap_servers.strip())
    else:
        logger.warning(
            "Kafka not configured (KAFKA_BOOTSTRAP_SERVERS not set) - messaging disabled"
        )
    {%- endif %}

    return BikeInventoryService(bike_repository, message_publisher)


BikeServiceDependency = Annotated[BikeInventoryService, Depends(get_bike_service)]
