from typing import Annotated

from fastapi import Depends, Request

from app.adapters.llm import LiteLLMClient
from app.adapters.persistence import NoOpValidationReportRepository
from app.adapters.web.schemas import AccessoryTestInput
from app.domain.validation_service import ProductValidationService
from app.domain.validations.accessories.suite import build_accessory_validation_service


def get_validation_service(request: Request) -> ProductValidationService:
    """Build the accessory suite with its LLM client and configured repository."""
    return build_accessory_validation_service(
        request.app.state.litellm_client,
        repository=request.app.state.validation_report_repository,
    )


ValidationServiceDependency = Annotated[
    ProductValidationService,
    Depends(get_validation_service),
]


def build_testing_validation_service(
    request: Request, accessory: AccessoryTestInput
) -> ProductValidationService:
    """Build the accessory suite with caller-supplied LLM settings.

    Neither the report nor the LLM requests are stored.
    """
    config = request.app.state.litellm_client.config.with_settings(
        accessory.llm_settings
    )
    return build_accessory_validation_service(
        LiteLLMClient(request.app.state.http_client, config),
        repository=NoOpValidationReportRepository(),
        criterion_settings=dict(accessory.criterion_settings.items()),
    )
