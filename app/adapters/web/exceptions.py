from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

from .schemas import ErrorListWebResponse, ErrorWebResponse


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
        content=error_response.model_dump(),
    )
