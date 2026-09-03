from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app.adapters.web.dependencies import get_accessory_classifier
from app.domain.accessory_classifier import AccessoryClassifier
from app.domain.entities import AccessoryClassification, ClassificationContext
from app.main import app


class MockAccessoryClassifier(AccessoryClassifier):
    """Test double that keeps HTTP tests independent of unfinished domain logic."""

    def __init__(self) -> None:
        self.last_context: ClassificationContext | None = None

    async def classify(
        self,
        accessory_name: str,
        context: ClassificationContext,
    ) -> AccessoryClassification:
        self.last_context = context
        return AccessoryClassification(
            accessory_name=accessory_name,
            is_leasable=True,
            description="Mocked accessory description",
            evaluated_rules={"mock_rule": True},
        )


@pytest.fixture
def mock_classifier() -> MockAccessoryClassifier:
    return MockAccessoryClassifier()


@pytest.fixture
def test_client(mock_classifier: MockAccessoryClassifier) -> Iterator[TestClient]:
    app.dependency_overrides[get_accessory_classifier] = lambda: mock_classifier
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()
