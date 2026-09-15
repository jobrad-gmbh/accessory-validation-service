from typing import Any

from fastapi import APIRouter, status


system_router = APIRouter(
    tags=["system"],
)


@system_router.get("/", status_code=status.HTTP_200_OK)
async def root() -> dict[str, str]:
    return {"message": "Accessory Validator"}


@system_router.get("/health", status_code=status.HTTP_200_OK)
async def health_check() -> dict[str, Any]:
    health_status: dict[str, Any] = {
        "status": "healthy",
        "service": "accessory-validator",
        "version": "1.0.0",
    }
    return health_status
