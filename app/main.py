from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
{%- if 'opentelemetry' in values.features %}
from prometheus_client import make_asgi_app, Counter, Summary
{%- endif %}

# Local imports
from app.adapters.web.bike_routes import bike_router
from app.adapters.web.system_routes import system_router
from app.adapters.web.exceptions import validation_exception_handler
from app.config.logging import setup_logging, get_logger
from app.config.settings import settings


setup_logging()
logger = get_logger(__name__)


{%- if 'opentelemetry' in values.features %}
REQUEST_COUNTER = Counter(
    "http_requests_total",
    "Total number of HTTP requests",
    ["method", "endpoint"],
)
REQUEST_LATENCY = Summary(
    "http_request_latency_seconds",
    "Duration of an HTTP request in seconds",
    ["method", "endpoint"],
)
{%- endif %}

app = FastAPI(
    title="${{ values.projectName }}",
)


{%- if 'opentelemetry' in values.features %}
@app.middleware("http")
async def prometheus_middleware(request: Request, call_next):
    """Middleware to record prometheus metrics."""
    method = request.method
    endpoint = request.url.path

    with REQUEST_LATENCY.labels(method=method, endpoint=endpoint).time():
        response = await call_next(request)
    REQUEST_COUNTER.labels(method=method, endpoint=endpoint).inc()

    return response
{%- endif %}


{%- if 'opentelemetry' in values.features %}
metrics_app = make_asgi_app()
# NOTE this creates an endpoint /metrics/
# so the OTL collector must also look for /metrics/ (mind the slash)
app.mount("/metrics", metrics_app)
{%- endif %}


@app.exception_handler(RequestValidationError)
async def my_validation_exception_handler(
    request: Request, exc: RequestValidationError
):
    return await validation_exception_handler(request, exc)


# Include routers
app.include_router(system_router)
app.include_router(bike_router, prefix=settings.API_V1_BASE_URL)
