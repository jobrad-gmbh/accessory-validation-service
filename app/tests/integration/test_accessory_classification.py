from fastapi.testclient import TestClient

from app.config.settings import settings
from app.domain.entities import ClassificationContext
from app.tests.conftest import MockAccessoryClassifier


def test_classification_endpoint_uses_the_domain_service(
    test_client: TestClient,
    mock_classifier: MockAccessoryClassifier,
) -> None:
    response = test_client.post(
        f"{settings.API_V1_BASE_URL}/accessories/classify",
        json={
            "accessory_name": "front light",
            "context": {
                "company": "bawu",
                "employee_type": "state_employee",
            },
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "accessory_name": "front light",
        "is_leasable": True,
        "description": "Mocked accessory description",
        "evaluated_rules": {"mock_rule": True},
    }
    assert mock_classifier.last_context == ClassificationContext(
        company="bawu",
        employee_type="state_employee",
    )


def test_missing_accessory_name_uses_template_error_shape(
    test_client: TestClient,
) -> None:
    response = test_client.post(
        f"{settings.API_V1_BASE_URL}/accessories/classify",
        json={"context": {"company": "default"}},
    )

    assert response.status_code == 422
    assert response.json()["errors"][0]["code"] == "INVALID_PARAMETER"
