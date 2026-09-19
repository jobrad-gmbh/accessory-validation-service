from uuid import UUID

from fastapi.testclient import TestClient

from app.adapters.web.dependencies import get_validation_service
from app.domain.validation import (
    SimpleValidation,
)
from app.domain.validation_results import (
    ValidationResult,
    ValidationStatus,
)
from app.domain.validation_service import (
    ProductValidationService,
)
from app.main import app


def payload(**overrides):
    value = {
        "brand": "Example",
        "model": "Rear rack",
        "price": "49.99",
        "origin": {"source": "odoo", "external_ref": "ACC-42"},
    }
    value.update(overrides)
    return value


def test_validate_accessory_returns_the_domain_report(test_client: TestClient):
    received_requests = []

    class AlwaysPasses(SimpleValidation):
        id = "test_validation"

        async def evaluate_result(self, request):
            received_requests.append(request)
            return ValidationResult(
                status=ValidationStatus.PASSED,
                details="The deterministic API test validation passed.",
            )

    app.dependency_overrides[get_validation_service] = lambda: (
        ProductValidationService([AlwaysPasses()])
    )

    response = test_client.post("/api/v1/accessories/validate", json=payload())

    assert response.status_code == 200
    body = response.json()
    UUID(body["product_id"])
    assert body["status"] == "VALID"
    assert body["validations"][0]["validation_id"] == "test_validation"
    assert body["validations"][0]["status"] == "PASSED"
    assert received_requests[0].context.is_bawu_order is False


def test_validate_accessory_passes_the_supplied_context(test_client: TestClient):
    contexts = []

    class RecordsContext(SimpleValidation):
        id = "records_context"

        async def evaluate_result(self, request):
            contexts.append(request.context)
            return ValidationResult(
                status=ValidationStatus.REJECTED,
                details="The deterministic API test validation rejected the accessory.",
            )

    app.dependency_overrides[get_validation_service] = lambda: (
        ProductValidationService([RecordsContext()])
    )

    response = test_client.post(
        "/api/v1/accessories/validate",
        json=payload(context={"is_bawu_order": True}),
    )

    assert response.status_code == 200
    assert response.json()["status"] == "INVALID"
    assert contexts[0].is_bawu_order is True


def test_validate_accessory_returns_structured_input_errors(test_client: TestClient):
    response = test_client.post(
        "/api/v1/accessories/validate",
        json=payload(price="-1", brand=""),
    )

    assert response.status_code == 422
    errors = response.json()["errors"]
    assert {error["code"] for error in errors} == {"INVALID_PARAMETER"}
    assert any("body.brand" in error["message"] for error in errors)
    assert any("body.price" in error["message"] for error in errors)


def test_validate_accessory_maps_technical_failures(test_client: TestClient):
    class Fails(SimpleValidation):
        id = "failing_validation"

        async def evaluate_result(self, request):
            raise RuntimeError("External dependency failed")

    app.dependency_overrides[get_validation_service] = lambda: (
        ProductValidationService([Fails()])
    )

    response = test_client.post("/api/v1/accessories/validate", json=payload())

    assert response.status_code == 503
    assert response.json() == {
        "errors": [
            {
                "code": "VALIDATION_EXECUTION_ERROR",
                "message": "The validation could not be completed.",
                "details": "Validation failing_validation failed",
            }
        ]
    }


def test_default_validation_is_reachable(test_client: TestClient):
    response = test_client.post("/api/v1/accessories/validate", json=payload())

    assert response.status_code == 200
    body = response.json()
    assert body["status"] in {"VALID", "INVALID", "UNDETERMINED"}
    assert body["validations"][0]["validation_id"] == "accessory_leasability"
