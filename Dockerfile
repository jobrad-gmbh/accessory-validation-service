FROM python:${{ values.pythonVersion }}-alpine3.22 AS builder

{%- if 'kafka' in values.features %}
RUN apk add --no-cache \
    librdkafka-dev \
    build-base
{%- endif %}

RUN pip install poetry==2.1.1

ENV POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_IN_PROJECT=1 \
    POETRY_VIRTUALENVS_CREATE=1 \
    POETRY_CACHE_DIR=/tmp/poetry_cache

WORKDIR /app/

COPY pyproject.toml poetry.lock ./

RUN --mount=type=cache,target=$POETRY_CACHE_DIR poetry install --only main --no-root

FROM python:${{ values.pythonVersion }}-alpine3.22 AS runtime

WORKDIR /service/

ENV VIRTUAL_ENV=/app/.venv \
    PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1

COPY --from=builder ${VIRTUAL_ENV} ${VIRTUAL_ENV}

COPY ./app ./app
COPY ./alembic ./alembic
COPY ./alembic.ini .
COPY ./entrypoint.sh .
RUN chmod +x ./entrypoint.sh

RUN addgroup -S appgroup && adduser -S appuser -G appgroup
USER appuser

EXPOSE ${{ values.port }}

ENTRYPOINT [ "./entrypoint.sh" ]
