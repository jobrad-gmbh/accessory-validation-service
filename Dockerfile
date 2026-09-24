FROM python:3.14-alpine3.22

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
COPY ./entrypoint.sh ./entrypoint.sh
RUN chmod +x ./entrypoint.sh \
    && addgroup -S appgroup \
    && adduser -S appuser -G appgroup

USER appuser
EXPOSE 8000

ENTRYPOINT ["./entrypoint.sh"]
