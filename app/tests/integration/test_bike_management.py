from fastapi.testclient import TestClient

from app.config.settings import settings


def test_fetching_newly_created_bike(db_test_client: TestClient):
    """
    End-to-end test: Create a bike via POST and verify it can be retrieved via GET.
    Uses testcontainers PostgreSQL for real database interaction.
    """
    new_bike_data = '{"brand": "Canyon", "model": "Grail", "bike_type": "GRAVEL"}'

    # Create bike via POST
    create_response = db_test_client.post(
        f"{settings.API_V1_BASE_URL}/bikes/",
        content=new_bike_data,
        headers={"Content-Type": "application/json"},
    )

    # Verify creation response
    assert create_response.status_code == 201
    assert create_response.headers["Content-Type"] == "application/json"
    created_bike = create_response.json()

    # Verify created bike has expected data
    assert created_bike["brand"] == "Canyon"
    assert created_bike["model"] == "Grail"
    assert created_bike["bike_type"] == "GRAVEL"
    assert "id" in created_bike
    assert isinstance(created_bike["id"], int)
    created_bike_id = created_bike["id"]

    # Retrieve bike via GET
    get_response = db_test_client.get(
        f"{settings.API_V1_BASE_URL}/bikes/{created_bike_id}",
        headers={"Accept": "application/json"},
    )

    # Verify retrieval response
    assert get_response.status_code == 200
    retrieved_bike = get_response.json()

    # Verify retrieved bike matches created bike
    assert retrieved_bike == created_bike
    assert retrieved_bike["id"] == created_bike_id
    assert retrieved_bike["brand"] == "Canyon"
    assert retrieved_bike["model"] == "Grail"
    assert retrieved_bike["bike_type"] == "GRAVEL"


def test_creating_bike_with_missing_property_should_return_error(
    db_test_client: TestClient,
):
    """
    Test that creating a bike with missing required property returns validation error.
    """
    new_bike_data = '{"brand": "Canyon", "bike_type": "GRAVEL"}'

    # Create bike via POST with missing model field
    create_response = db_test_client.post(
        f"{settings.API_V1_BASE_URL}/bikes/",
        content=new_bike_data,
        headers={"Content-Type": "application/json"},
    )

    # Verify error response
    assert create_response.status_code >= 400 and create_response.status_code < 500
    assert create_response.headers["Content-Type"] == "application/json"
    error_response = create_response.json()

    # Verify error structure
    assert "errors" in error_response
    assert isinstance(error_response["errors"], list)
    assert len(error_response["errors"]) > 0

    error = error_response["errors"][0]
    assert error["code"] == "INVALID_PARAMETER"
    assert "message" in error and error["message"]
    assert "details" in error and "model" in error["details"]


def test_fetching_bike_list_with_fresh_application(db_test_client: TestClient):
    """
    Test fetching multiple bikes when database is empty returns proper structure.
    """
    # Get bikes list
    list_response = db_test_client.get(
        f"{settings.API_V1_BASE_URL}/bikes",
        headers={"Accept": "application/json"},
    )

    # Verify response
    assert list_response.status_code == 200
    assert list_response.headers["Content-Type"] == "application/json"
    bikes_list = list_response.json()

    # Verify response structure
    assert "data" in bikes_list
    assert isinstance(bikes_list["data"], list)
    assert len(bikes_list["data"]) == 0
