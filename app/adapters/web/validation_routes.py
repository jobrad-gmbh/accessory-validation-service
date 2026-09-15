from fastapi import APIRouter, status

from app.adapters.web.dependencies import ValidationServiceDependency
from app.adapters.web.schemas import AccessoryInput, ValidationReportResponse


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
