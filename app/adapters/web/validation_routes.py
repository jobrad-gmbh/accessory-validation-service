from fastapi import APIRouter, Request, status

from app.adapters.web.dependencies import (
    ValidationServiceDependency,
    build_testing_validation_service,
)
from app.adapters.web.schemas import (
    AccessoryInput,
    AccessoryTestInput,
    AccessoryTestReportResponse,
    ValidationReportResponse,
)


validation_router = APIRouter(prefix="/accessories", tags=["validations"])


@validation_router.post(
    "/validate",
    response_model=ValidationReportResponse,
    status_code=status.HTTP_200_OK,
)
async def validate_accessory(
    accessory: AccessoryInput,
    service: ValidationServiceDependency,
) -> ValidationReportResponse:
    report = await service.validate(accessory.to_domain())
    return ValidationReportResponse.from_domain(report)


@validation_router.post(
    "/validate/test",
    response_model=AccessoryTestReportResponse,
    response_model_exclude_unset=True,
    status_code=status.HTTP_200_OK,
    summary="Test accessory validation without storing results",
)
async def test_validate_accessory(
    accessory: AccessoryTestInput,
    request: Request,
) -> AccessoryTestReportResponse:
    service = build_testing_validation_service(request, accessory)
    report = await service.validate(accessory.to_domain())
    return AccessoryTestReportResponse.from_domain(
        report, include_product_information=accessory.include_product_information
    )
