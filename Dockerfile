FROM python:3.14.5-alpine3.22 AS builder

RUN pip install --no-cache-dir poetry==2.1.1

ENV POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_IN_PROJECT=1 \
    POETRY_VIRTUALENVS_CREATE=1 \
    POETRY_CACHE_DIR=/tmp/poetry_cache

WORKDIR /app
COPY pyproject.toml poetry.lock* ./
RUN --mount=type=cache,target=/tmp/poetry_cache poetry install --only main --no-root

FROM python:3.14.5-alpine3.22 AS runtime

WORKDIR /service
ENV VIRTUAL_ENV=/app/.venv \
    PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1

COPY --from=builder /app/.venv /app/.venv
COPY ./app ./app
COPY ./entrypoint.sh ./entrypoint.sh
RUN chmod +x ./entrypoint.sh && addgroup -S appgroup && adduser -S appuser -G appgroup
USER appuser

EXPOSE 8000
ENTRYPOINT ["./entrypoint.sh"]
