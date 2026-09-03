from fastapi import APIRouter

from app.adapters.web.dependencies import AccessoryClassifierDependency
from app.adapters.web.schemas import (
    AccessoryClassificationWebRequest,
    AccessoryClassificationWebResponse,
)
from app.domain.entities import ClassificationContext

accessory_router = APIRouter(prefix="/accessories", tags=["accessories"])


@accessory_router.post(
    "/classify",
    response_model=AccessoryClassificationWebResponse,
)
async def classify_accessory(
    request: AccessoryClassificationWebRequest,
    classifier: AccessoryClassifierDependency,
) -> AccessoryClassificationWebResponse:
    result = await classifier.classify(
        request.accessory_name,
        ClassificationContext(
            company=request.context.company,
            employee_type=request.context.employee_type,
        ),
    )
    return AccessoryClassificationWebResponse.model_validate(result.model_dump())
