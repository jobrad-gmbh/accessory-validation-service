from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError

from app.adapters.llm import (
    JevClient,
    LiteLLMClient,
    RecordingLLMClient,
)
from app.adapters.web.exceptions import (
    validation_configuration_exception_handler,
    validation_exception_handler,
    validation_execution_exception_handler,
)
from app.adapters.web.system_routes import system_router
from app.adapters.web.validation_routes import validation_router
from app.config.logging import setup_logging
from app.config.settings import settings
from app.domain.errors import (
    ValidationConfigurationError,
    ValidationExecutionError,
)
from app.domain.validation_repository import ValidationReportRepository

setup_logging()


@asynccontextmanager
async def lifespan(application: FastAPI) -> AsyncGenerator[None]:
    repository: ValidationReportRepository | None = getattr(
        application.state, "validation_report_repository", None
    )
    if repository is None:
        raise ValidationConfigurationError(
            "Repository is required; configure "
            "app.state.validation_report_repository before startup"
        )
    async with httpx.AsyncClient() as http_client:
        application.state.litellm_client = RecordingLLMClient(
            LiteLLMClient(http_client)
        )
        application.state.jev_client = JevClient(http_client)
        yield


app = FastAPI(
    title="Accessory Validator",
    lifespan=lifespan,
)


@app.exception_handler(RequestValidationError)
async def my_validation_exception_handler(
    request: Request, exc: RequestValidationError
):
    return await validation_exception_handler(request, exc)


@app.exception_handler(ValidationConfigurationError)
async def configuration_exception_handler(
    request: Request, exc: ValidationConfigurationError
):
    return await validation_configuration_exception_handler(request, exc)


@app.exception_handler(ValidationExecutionError)
async def execution_exception_handler(
    request: Request, exc: ValidationExecutionError
):
    return await validation_execution_exception_handler(request, exc)


app.include_router(system_router)
app.include_router(validation_router, prefix=settings.API_V1_BASE_URL)
