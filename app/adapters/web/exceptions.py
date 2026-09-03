from fastapi import Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.adapters.web.schemas import ErrorListWebResponse, ErrorWebResponse


async def validation_exception_handler(
    _: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    errors = []
    for error in exc.errors():
        field_path = ".".join(str(location) for location in error["loc"])
        errors.append(
            ErrorWebResponse(
                code="INVALID_PARAMETER",
                message=f"Validation failed for field '{field_path}'",
                details=error["msg"],
            )
        )

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=ErrorListWebResponse(errors=errors).model_dump(),
    )
