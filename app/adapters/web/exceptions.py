import logging

from fastapi import Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.adapters.llm.errors import LLMError
from app.domain.errors import (
    ValidationConfigurationError,
    ValidationExecutionError,
)

from .schemas import ErrorListWebResponse, ErrorWebResponse

logger = logging.getLogger("accessory_validator")


async def validation_exception_handler(
    _: Request, exc: RequestValidationError
) -> JSONResponse:
    """
    Custom exception handler for validation errors.
    Formats validation errors according to the ErrorResponse schema.
    """
    error_details: list[ErrorWebResponse] = []

    for error in exc.errors():
        # Extract field location (e.g., ['body', 'brand'] -> 'body.brand')
        field_path = ".".join(str(loc) for loc in error["loc"])

        # Create error detail
        error_detail = ErrorWebResponse(
            code="INVALID_PARAMETER",
            message=f"Validation failed for field '{field_path}': {error['msg']}",
            details=f"Field: {field_path}, Input: {error.get('input', 'N/A')}, Type: {error['type']}",
        )
        error_details.append(error_detail)

    error_response = ErrorListWebResponse(errors=error_details)

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=error_response.model_dump(mode="json"),
    )


async def validation_configuration_exception_handler(
    _: Request, exc: ValidationConfigurationError
) -> JSONResponse:
    return _domain_error_response(
        status.HTTP_500_INTERNAL_SERVER_ERROR,
        "VALIDATION_CONFIGURATION_ERROR",
        "The validation process is not configured correctly.",
        str(exc),
    )


async def validation_execution_exception_handler(
    _: Request, exc: ValidationExecutionError
) -> JSONResponse:
    details = str(exc)
    if isinstance(exc.__cause__, LLMError):
        details = str(exc.__cause__)
        logger.warning("Validation failed: %s", details)
    return _domain_error_response(
        status.HTTP_503_SERVICE_UNAVAILABLE,
        "VALIDATION_EXECUTION_ERROR",
        "The validation could not be completed.",
        details,
    )


def _domain_error_response(
    status_code: int,
    code: str,
    message: str,
    details: str,
) -> JSONResponse:
    response = ErrorListWebResponse(
        errors=[ErrorWebResponse(code=code, message=message, details=details)]
    )
    return JSONResponse(
        status_code=status_code,
        content=response.model_dump(mode="json"),
    )
