from typing import Annotated

from fastapi import Depends

from app.domain.validation_service import ProductValidationService
from app.domain.validations.accessories.suite import build_accessory_validation_service


def get_validation_service() -> ProductValidationService:
    """Provide the accessory validation suite to HTTP handlers."""
    return build_accessory_validation_service()


ValidationServiceDependency = Annotated[
    ProductValidationService,
    Depends(get_validation_service),
]
