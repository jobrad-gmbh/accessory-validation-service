from typing import Dict, Any

from fastapi import APIRouter, status
from app.config.logging import get_logger

logger = get_logger(__name__)


system_router = APIRouter(
    tags=["system"],
)


@system_router.get("/", status_code=status.HTTP_200_OK)
async def root() -> Dict[str, str]:
    return {"message": "Hello from ${{ values.projectName }}"}


@system_router.get("/health", status_code=status.HTTP_200_OK)
async def health_check() -> Dict[str, Any]:
    health_status: Dict[str, Any] = {
        "status": "healthy",
        "service": "${{ values.projectNameKebab }}",
        "version": "1.0.0",
    }
    # TODO Consider checking other system components like database, kafka, etc.

    return health_status
