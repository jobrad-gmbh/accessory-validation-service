from fastapi.testclient import TestClient


def test_root_endpoint_returns_data(test_client: TestClient):
    response = test_client.get("/")

    assert response.status_code == 200
    assert response.headers["Content-Type"] == "application/json"

    data = response.json()
    assert data["message"] == "Hello from ${{ values.projectName }}"


def test_health_check_endpoint_is_reacheable(test_client: TestClient):
    response = test_client.get("/health")

    assert response.status_code == 200
    assert response.headers["Content-Type"] == "application/json"

    health_data = response.json()
    assert health_data["status"] == "healthy"
    assert health_data["service"] == "${{ values.projectNameKebab }}"
    assert "version" in health_data
