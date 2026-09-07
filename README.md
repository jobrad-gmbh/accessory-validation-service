# ${{ values.projectName }}

${{ values.projectDescription }}

## Quick Start

```bash
# Install dependencies, setup environment
make setup

# Start development server
make start

# Run tests
make test
```

## API Endpoints

- `GET /` - Welcome message
- `GET /health` - Health check
{%- if 'postgresql' in values.features %}
- `GET /api/v1/bikes` - List bikes
- `POST /api/v1/bikes` - Create bike
{%- endif %}
{%- if 'opentelemetry' in values.features %}
- `GET /metrics` - Prometheus metrics
{%- endif %}

## Architecture

FastAPI service using hexagonal architecture:
- `app/domain/` - Business logic
- `app/adapters/` - External interfaces (web, database, messaging)
- `app/config/` - Configuration and logging

## Tech Stack

- **Framework:** FastAPI + Uvicorn
- **Python:** ${{ values.pythonVersion }}
{%- if 'postgresql' in values.features %}
- **Database:** PostgreSQL + SQLAlchemy + Alembic
{%- endif %}
{%- if 'kafka' in values.features %}
- **Messaging:** Apache Kafka
{%- endif %}
{%- if 'opentelemetry' in values.features %}
- **Monitoring:** Prometheus + OpenTelemetry
{%- endif %}
- **Deployment:** Nomad + Docker

## Development

Available commands via `make help`
