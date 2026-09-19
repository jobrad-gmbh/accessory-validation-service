from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError

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

setup_logging()


app = FastAPI(
    title="Accessory Validator",
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


# Include routers
app.include_router(system_router)
app.include_router(validation_router, prefix=settings.API_V1_BASE_URL)
