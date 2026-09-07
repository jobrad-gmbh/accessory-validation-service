import json
from typing import Any
from aiokafka import AIOKafkaProducer  # type: ignore
from app.domain.ports import MessagePublisher

from app.config.logging import get_logger

logger = get_logger(__name__)


class KafkaMessagePublisher(MessagePublisher):
    """Kafka implementation of message publisher."""

    def __init__(self, bootstrap_servers: str):
        self.bootstrap_servers = bootstrap_servers
        self._producer: AIOKafkaProducer | None = None

    async def _ensure_producer(self) -> AIOKafkaProducer:
        """Ensure producer is initialized and started."""
        if self._producer is None:
            try:
                self._producer = AIOKafkaProducer(
                    bootstrap_servers=self.bootstrap_servers,
                    value_serializer=lambda value: json.dumps(value).encode("utf-8"),
                    # Add connection timeout and retry settings
                    request_timeout_ms=10000,
                    retry_backoff_ms=500,
                    # Add metadata timeout to fail fast
                    metadata_max_age_ms=30000,
                    # Set max block time for send operations
                    max_batch_size=16384,
                    linger_ms=0,  # Send immediately
                )
                await self._producer.start()
                logger.info(
                    f"Kafka producer started successfully, connected to {self.bootstrap_servers}"
                )
            except Exception as e:
                logger.error(f"Failed to start Kafka producer: {e}")
                # Clean up the failed producer
                if self._producer:
                    try:
                        await self._producer.stop()
                    except Exception:
                        pass
                self._producer = None
                raise
        return self._producer

    async def publish(self, topic: str, message: dict[str, Any]) -> None:
        """Publish a message to a Kafka topic."""
        try:
            producer = await self._ensure_producer()
            await producer.send_and_wait(topic, value=message)
            logger.debug(
                f"Successfully published message to topic '{topic}': {message}"
            )
        except Exception as e:
            logger.error(f"Failed to publish message to topic '{topic}': {e}")
            # Clean up the producer on any error
        finally:
            await self.close()

    async def close(self) -> None:
        """Close the producer connection."""
        if self._producer:
            try:
                await self._producer.stop()
                logger.info("Kafka producer stopped successfully")
            except Exception as e:
                logger.error(f"Error stopping Kafka producer: {e}")
            finally:
                self._producer = None
