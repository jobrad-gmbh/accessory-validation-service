SHELL = /bin/sh

.DEFAULT_GOAL := help

GREEN = \033[1;32m
RED = \033[1;31m
MAGENTA = \033[1;35m
ORANGE = \033[1;33m
BOLD = \033[1m
RESET = \033[0m
DONE = $(GREEN)[ OK ] ✨ $(RESET)
SKIP = $(MAGENTA)[SKIP] ⏭️ $(RESET)
ERROR = $(RED)[STOP] 🛑 $(RESET)
WARN = $(ORANGE)[WARN] ⚠️ $(RESET)

# Print out all the comments which are prefixed with ## (instead of only one #)
.PHONY: help
help:
	@echo "$(BOLD)Available targets$(RESET)\n"
	@awk '/^##/{print substr($$0, 3)}' $(MAKEFILE_LIST)

## 🚀 start
## Start the application with database and Kafka services
##
.PHONY: start
start: {%if 'postgresql' in values.features %}database-up{% endif %} {% if 'kafka' in values.features %}kafka-up{%- endif %}
	@echo "Starting the application..."
	@poetry run uvicorn app.main:app --host 127.0.0.1 --port ${{ values.port }} --reload

.PHONY: setup
setup:
	@echo "Setting up the environment..."
	@poetry install --no-root
	@cp .env.example .env || echo "No .env.example file found, skipping copy."
{%- if 'postgresql' in values.features %}
	@make database-migration
{%- endif %}
{% if 'postgresql' in values.features %}
.PHONY: database-up
database-up:
	@echo "Starting database..."
	@docker compose up --wait db
{%- endif %}
{% if 'kafka' in values.features %}
.PHONY: kafka-up
kafka-up:
	@echo "Starting kafka..."
	@docker compose up -d kafka kafka-ui
{%- endif %}
{% if 'postgresql' in values.features %}
## 🔧 database-migration
## Run database migration on local database
##
.PHONY: database-migration
database-migration: database-up
	@echo "Running database migrations..."
	@poetry run alembic upgrade head
{%- endif %}

## 🧪 test
## Run tests with pytest
##
.PHONY: test
test:
	@echo "Running tests..."
	@poetry run pytest
