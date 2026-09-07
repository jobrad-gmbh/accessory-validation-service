import json
import asyncio
from typing import Any, Dict, List
from fastapi.testclient import TestClient
from aiokafka import AIOKafkaConsumer  # type: ignore

from app.config.settings import settings


async def consume_messages_from_kafka(
    bootstrap_servers: str, topic: str, timeout: int = 10
) -> List[Dict[str, Any]]:
    """Consume messages from Kafka topic and return them."""
    consumer = AIOKafkaConsumer(
        topic,
        bootstrap_servers=bootstrap_servers,
        group_id="test-consumer-group",
        auto_offset_reset="earliest",
        value_deserializer=lambda m: json.loads(m.decode("utf-8")),  # type: ignore
    )

    messages: List[Dict[str, Any]] = []

    try:
        await consumer.start()

        # Wait for messages with timeout
        end_time = asyncio.get_event_loop().time() + timeout

        while asyncio.get_event_loop().time() < end_time:
            try:
                # Check for messages with a short timeout
                data = await asyncio.wait_for(
                    consumer.getmany(timeout_ms=1000), timeout=2.0
                )  # type: ignore

                for topic_partition, msgs in data.items():  # type: ignore
                    for msg in msgs:  # type: ignore
                        messages.append(msg.value)  # type: ignore

                # If we got messages, we can stop waiting
                if messages:
                    break

            except asyncio.TimeoutError:
                # Continue waiting until overall timeout
                continue
        return messages

    finally:
        await consumer.stop()  # type: ignore


def test_bike_creation_publishes_kafka_message(
    full_test_client: TestClient, test_kafka_container: str
) -> None:
    """
    E2E test: Create a bike and verify the event is published to Kafka.
    Uses real Kafka container for integration testing.
    """
    # Create a bike via API
    bike_data = {"brand": "Specialized", "model": "Roubaix", "bike_type": "ROAD"}

    create_response = full_test_client.post(  # type: ignore
        f"{settings.API_V1_BASE_URL}/bikes/",
        json=bike_data,
        headers={"Content-Type": "application/json"},
    )

    # Verify bike creation was successful
    assert create_response.status_code == 201  # type: ignore
    created_bike: Dict[str, Any] = create_response.json()  # type: ignore
    assert created_bike["brand"] == "Specialized"
    assert created_bike["model"] == "Roubaix"
    assert created_bike["bike_type"] == "ROAD"
    assert "id" in created_bike

    bike_id: int = created_bike["id"]

    # Now verify that a message was published to Kafka
    async def check_kafka_message() -> Dict[str, Any]:
        messages = await consume_messages_from_kafka(
            bootstrap_servers=test_kafka_container,
            topic="bike-events",
            timeout=15,  # Give some time for the message to be published
        )

        # Should have at least one message
        assert len(messages) > 0, "No messages found in Kafka topic"

        # Find our bike creation message
        bike_creation_message: Dict[str, Any] | None = None
        for message in messages:
            if (
                message.get("event_type") == "bike_created"
                and message.get("bike_id") == bike_id
            ):
                bike_creation_message = message
                break

        assert bike_creation_message is not None, (
            f"Bike creation message not found for bike {bike_id}"
        )

        # Verify message structure and content
        assert bike_creation_message["event_type"] == "bike_created"
        assert bike_creation_message["bike_id"] == bike_id
        assert bike_creation_message["brand"] == "Specialized"
        assert bike_creation_message["model"] == "Roubaix"
        assert bike_creation_message["bike_type"] == "ROAD"

        return bike_creation_message

    # Run the async function
    message: Dict[str, Any] = asyncio.run(check_kafka_message())

    # Additional verification
    assert isinstance(message["bike_id"], int)
    assert message["bike_id"] > 0


def test_multiple_bike_creations_publish_multiple_messages(
    full_test_client: TestClient, test_kafka_container: str
) -> None:
    """
    E2E test: Create multiple bikes and verify all events are published.
    """
    bikes_to_create = [
        {"brand": "Trek", "model": "Madone", "bike_type": "ROAD"},
        {"brand": "Giant", "model": "Trance", "bike_type": "MOUNTAIN"},
        {"brand": "Cannondale", "model": "Topstone", "bike_type": "GRAVEL"},
    ]

    created_bikes: List[Dict[str, Any]] = []

    # Create multiple bikes
    for bike_data in bikes_to_create:
        response = full_test_client.post(  # type: ignore
            f"{settings.API_V1_BASE_URL}/bikes/",
            json=bike_data,
            headers={"Content-Type": "application/json"},
        )
        assert response.status_code == 201  # type: ignore
        created_bikes.append(response.json())  # type: ignore

    # Verify all messages were published
    async def check_all_kafka_messages() -> List[Dict[str, Any]]:
        messages = await consume_messages_from_kafka(
            bootstrap_servers=test_kafka_container, topic="bike-events", timeout=20
        )

        # Should have at least as many messages as bikes created
        assert len(messages) >= len(created_bikes), (
            f"Expected at least {len(created_bikes)} messages, got {len(messages)}"
        )

        # Verify each bike has a corresponding message
        created_bike_ids = {bike["id"] for bike in created_bikes}
        message_bike_ids = {
            msg["bike_id"]
            for msg in messages
            if msg.get("event_type") == "bike_created"
            and msg.get("bike_id") in created_bike_ids
        }

        assert created_bike_ids == message_bike_ids, (
            "Not all created bikes have corresponding Kafka messages"
        )

        return messages

    # Run the async function
    messages: List[Dict[str, Any]] = asyncio.run(check_all_kafka_messages())

    # Additional verification - check that each bike's data is correct in the messages
    for bike in created_bikes:
        bike_message: Dict[str, Any] | None = next(
            (
                msg
                for msg in messages
                if msg.get("bike_id") == bike["id"]
                and msg.get("event_type") == "bike_created"
            ),
            None,
        )
        assert bike_message is not None
        assert bike_message["brand"] == bike["brand"]
        assert bike_message["model"] == bike["model"]
        assert bike_message["bike_type"] == bike["bike_type"]
