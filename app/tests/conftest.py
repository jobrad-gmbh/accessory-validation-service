import pytest
from typing import Any
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, Engine
from sqlalchemy.orm import sessionmaker, Session
from testcontainers.postgres import PostgresContainer  # type: ignore
from testcontainers.kafka import KafkaContainer  # type: ignore
from app.adapters.messaging.kafka import KafkaMessagePublisher
from app.main import app
from app.adapters.persistence.sql_models import BaseSQLModel
from app.adapters.web.dependencies import get_bike_service
from app.domain.bike_inventory_service import BikeInventoryService
from app.adapters.persistence.repositories import SQLAlchemyBikeRepository
from app.domain.ports import MessagePublisher


@asynccontextmanager
async def test_lifespan(app: FastAPI):
    """Test lifespan that does nothing - tests control their own setup."""
    yield


@pytest.fixture
def test_postgres_container():
    """Start PostgreSQL container and return its connection URL."""
    with PostgresContainer("postgres:17.3-alpine3.21") as postgres:
        yield postgres.get_connection_url()


@pytest.fixture
def test_kafka_container():
    """Start a Kafka container for testing and return the bootstrap server URL."""
    kafka_container = KafkaContainer("confluentinc/cp-kafka:7.4.5")
    kafka_container.start()
    bootstrap_server = kafka_container.get_bootstrap_server()
    yield bootstrap_server
    kafka_container.stop()


@pytest.fixture
def test_engine(test_postgres_container: str) -> Engine:
    """Create test database engine."""
    engine = create_engine(test_postgres_container)
    # Create all tables in the test database
    BaseSQLModel.metadata.create_all(engine)
    return engine


@pytest.fixture
def test_session(test_engine: Engine):
    """Create test database session."""
    TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    session: Session = TestSessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture
def full_test_client(test_engine: Engine, test_kafka_container: str):
    """Create test client with overridden bike use-case dependency."""

    def override_get_bike_service():
        """Override bike service to use Postgres and Kafka container."""
        bike_repository = SQLAlchemyBikeRepository(test_engine)
        message_publisher = KafkaMessagePublisher(test_kafka_container.strip())

        return BikeInventoryService(bike_repository, message_publisher)

    # Override dependencies and lifespan
    app.dependency_overrides[get_bike_service] = override_get_bike_service
    original_lifespan = app.router.lifespan_context
    app.router.lifespan_context = test_lifespan

    with TestClient(app) as client:
        yield client

    # Restore original state
    app.dependency_overrides.clear()
    app.router.lifespan_context = original_lifespan


@pytest.fixture
def test_client():
    """Create test client without Postgres or Kafka container."""

    # Override lifespan to prevent migrations and other startup tasks
    original_lifespan = app.router.lifespan_context
    app.router.lifespan_context = test_lifespan

    with TestClient(app) as client:
        yield client

    # Restore original state
    app.router.lifespan_context = original_lifespan


@pytest.fixture
def db_test_client(test_engine: Engine):
    """Create test client with overridden bike use-case dependency but with mock Kafka."""

    def override_get_bike_service():
        """Override bike service to use Postgres container and a mocked Kafka."""
        bike_repository = SQLAlchemyBikeRepository(test_engine)

        class MockKafkaPublisher(MessagePublisher):
            async def publish(self, topic: str, message: dict[str, Any]) -> None:
                """Mock publish method that does nothing."""
                pass

        return BikeInventoryService(bike_repository, MockKafkaPublisher())

    # Override dependencies and lifespan
    app.dependency_overrides[get_bike_service] = override_get_bike_service
    original_lifespan = app.router.lifespan_context
    app.router.lifespan_context = test_lifespan

    with TestClient(app) as client:
        yield client

    # Restore original state
    app.dependency_overrides.clear()
    app.router.lifespan_context = original_lifespan
