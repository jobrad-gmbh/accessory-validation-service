import asyncio

import pytest

from app.adapters.web.schemas import AccessoryInput
from app.domain.errors import (
    ValidationExecutionError,
)
from app.domain.product import (
    Product,
    ProductContext,
    ProductOrigin,
    ProductType,
)
from app.domain.validation import (
    Validation,
    ValidationRequest,
)
from app.domain.validation_results import (
    ValidationExecution,
    ValidationResult,
    ValidationStatus,
)
from app.domain.validation_service import (
    ProductValidationService,
)


def product(*, external_ref: str = "ACC-42", category: str | None = None) -> Product:
    return Product(
        product_type=ProductType.ACCESSORY,
        brand="Example",
        model="Rack",
        category=category,
        origin=ProductOrigin(source="odoo", external_ref=external_ref),
    )


def validation_result():
    return ValidationResult(
        status=ValidationStatus.PASSED,
        details="Accessory is allowed.",
    )


def test_every_input_gets_a_new_product_id_even_with_the_same_origin():
    first = product()
    second = product()

    assert first.id != second.id
    assert first.origin == second.origin


def test_accessory_input_maps_origin_and_creates_a_new_product():
    submitted = AccessoryInput.model_validate(
        {
            "brand": "Example",
            "model": "Rack",
            "year": 2026,
            "category": "transport",
            "price": "49.99",
            "context": {},
            "origin": {"source": "odoo", "external_ref": "ACC-42"},
        }
    )

    first = submitted.to_domain().product
    second = submitted.to_domain().product

    assert first.id != second.id
    assert first.origin == ProductOrigin(source="odoo", external_ref="ACC-42")
    assert first.year == 2026
    assert first.category == "transport"


def test_validation_execution_owns_its_result():
    associated_product = product()

    execution = ValidationExecution(
        validation_id="accessory_leasability",
        product=associated_product,
        result=validation_result(),
    )

    assert execution.product is associated_product
    assert execution.result.status is ValidationStatus.PASSED
    assert not hasattr(execution, "product_id")


def test_validation_creates_an_execution():
    associated_product = product()

    class AlwaysPasses(Validation):
        id = "always_passes"

        async def evaluate_result(self, request):
            return validation_result()

    execution = asyncio.run(
        AlwaysPasses().validate(ValidationRequest(product=associated_product))
    )

    assert execution.product is associated_product
    assert execution.validation_id == "always_passes"
    assert execution.result.status is ValidationStatus.PASSED


def test_service_rejects_a_validation_execution_for_another_product():
    requested_product = product()
    other_product = product(external_ref="OTHER")

    class WrongProductValidation:
        id = "accessory_leasability"

        async def validate(self, request):
            return ValidationExecution(
                product=other_product,
                validation_id=self.id,
                result=validation_result(),
            )

    service = ProductValidationService([WrongProductValidation()])

    with pytest.raises(ValidationExecutionError, match="failed"):
        asyncio.run(service.validate(ValidationRequest(product=requested_product)))


def test_api_preserves_product_context_and_defaults_to_non_bawu():
    payload = {
        "brand": "Example",
        "model": "Rack",
        "price": "49.99",
        "origin": {"source": "odoo", "external_ref": "ACC-42"},
        "context": {"is_bawu_order": True},
    }
    assert AccessoryInput.model_validate(payload).to_domain().context == ProductContext(
        is_bawu_order=True
    )
    payload["context"] = {}
    assert (
        AccessoryInput.model_validate(payload).to_domain().context == ProductContext()
    )
    assert ValidationRequest(product=product()).context.is_bawu_order is False
