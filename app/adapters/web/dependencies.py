from typing import Annotated

from fastapi import Depends, Request

from app.domain.validation_service import ProductValidationService
from app.domain.validations.accessories.suite import build_accessory_validation_service


def get_validation_service(request: Request) -> ProductValidationService:
    """Build the accessory suite with the shared LiteLLM client."""
    return build_accessory_validation_service(request.app.state.litellm_client)


ValidationServiceDependency = Annotated[
    ProductValidationService,
    Depends(get_validation_service),
]
