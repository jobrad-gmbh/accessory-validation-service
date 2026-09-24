ARG PYTHON_VERSION=3.13
FROM python:${PYTHON_VERSION}-alpine3.22

RUN apk add --no-cache postgresql17-client

COPY --from=ghcr.io/astral-sh/uv:0.12.13 /uv /uvx /bin/

WORKDIR /service

ENV PATH="/service/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PORT=8000 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv uv sync --frozen --no-dev

COPY ./app ./app
COPY ./alembic ./alembic
COPY ./alembic.ini ./alembic.ini
COPY ./entrypoint.sh ./entrypoint.sh
RUN chmod +x ./entrypoint.sh \
    && addgroup -S appgroup \
    && adduser -S appuser -G appgroup

USER appuser
EXPOSE 8000

ENTRYPOINT ["./entrypoint.sh"]
