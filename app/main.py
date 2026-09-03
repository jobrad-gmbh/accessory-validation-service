from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.adapters.web.accessory_routes import accessory_router
from app.adapters.web.exceptions import validation_exception_handler
from app.adapters.web.system_routes import system_router
from app.config.logging import setup_logging
from app.config.settings import settings

setup_logging()

app = FastAPI(
    title="Accessory Validator",
    version="0.1.0",
    description="Classifies bicycle accessories for leasing eligibility.",
)


@app.exception_handler(RequestValidationError)
async def request_validation_exception_handler(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    return await validation_exception_handler(request, exc)


app.include_router(system_router)
app.include_router(accessory_router, prefix=settings.API_V1_BASE_URL)
