from fastapi.testclient import TestClient


def test_root_endpoint_returns_service_message(test_client: TestClient) -> None:
    response = test_client.get("/")

    assert response.status_code == 200
    assert response.json() == {"message": "Hello from Accessory Validator"}


def test_health_endpoint_returns_service_metadata(test_client: TestClient) -> None:
    response = test_client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "healthy",
        "service": "accessory-validator",
        "version": "0.1.0",
    }
