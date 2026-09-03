SHELL = /bin/sh

.DEFAULT_GOAL := help

.PHONY: help
help:
	@echo "Available targets"
	@awk '/^##/{print substr($$0, 3)}' $(MAKEFILE_LIST)

## setup     Install dependencies and create a local environment file
.PHONY: setup
setup:
	poetry install --no-root
	@test -f .env || cp .env.example .env

## start     Run the development server
.PHONY: start
start:
	poetry run uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload

## test      Run the test suite
.PHONY: test
test:
	poetry run pytest

## lint      Run static checks
.PHONY: lint
lint:
	poetry run ruff check app
	poetry run mypy app

## format    Format Python source
.PHONY: format
format:
	poetry run ruff format app
	poetry run ruff check --fix app
