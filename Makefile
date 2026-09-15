SHELL := /bin/sh

.DEFAULT_GOAL := help

.PHONY: help setup start test check

help:
	@printf "Available targets:\n  setup  Install dependencies\n  start  Run the API locally\n  test   Run tests\n  check  Run lint and type checks\n"

setup:
	uv sync --locked

start:
	uv run python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload

test:
	uv run python -m pytest

check:
	uv run python -m ruff check app tests
	uv run python -m mypy app
