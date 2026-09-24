# Accessory Validator

FastAPI service that runs the configured accessory validations and returns one
report containing their business results.

## Run locally

```bash
docker compose up -d postgres
uv sync --locked
uv run alembic upgrade head
uv run python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

The API documentation is available at <http://127.0.0.1:8000/docs>.
Set `POSTGRES_DB`, `POSTGRES_USER`, and `POSTGRES_PASSWORD` in `.env` for the
Compose database. `DATABASE_URL` reuses those values to connect local commands
through `localhost`; set it differently if PostgreSQL is elsewhere. To run both the
database and API in containers, fill in `.env` with your LiteLLM and Jev
settings, then use `docker compose up --build`. Compose builds the API's database
URL from the PostgreSQL values using the `postgres` service hostname. The API
container applies migrations before starting.

Products and validation executions are saved atomically. Criterion results are
returned in the validation response but are not stored separately. LLM requests
are saved as they happen, including failed requests.
Their `validation_execution_id` can be used to join successful validations to
their requests. Requests from a failed validation may have no matching execution.

## Validate an accessory

```bash
curl -X POST http://127.0.0.1:8000/api/v1/accessories/validate \
  -H 'Content-Type: application/json' \
  -d '{
    "brand": "Example",
    "model": "Rear rack",
    "category": "bicycle transport",
    "price": "49.99",
    "origin": {
      "source": "odoo",
      "external_ref": "ACC-42"
    },
    "context": {
      "is_bawu_order": false
    }
  }'
```

`context` is optional and defaults to a non-BAWU order.

## Development

```bash
uv run python -m pytest
uv run python -m ruff check app
uv run python -m mypy app
```

All current accessory leasability criteria use the configured LiteLLM gateway.

## Project structure

The top level separates business behavior (`domain`), external communication
(`adapters`), configuration (`config`), and application assembly (`main.py`).

```text
app/
├── main.py
├── config/
├── adapters/
│   ├── web/
│   └── llm/
└── domain/
    ├── criterion.py                  # Criterion answers and results
    ├── product.py
    ├── validation.py
    ├── validation_results.py
    ├── validation_service.py
    ├── errors.py
    └── validations/
        └── accessories/
            ├── suite.py
            └── leasability/
                ├── validation.py
                ├── strategies.py
                ├── criteria.py       # Accessory leasability criteria
                └── prompts/          # LLM instructions in Markdown
```

- `domain/product.py` defines submitted product data, origin, business context,
  and the existing product-resolution contract.
- `domain/validation.py` defines the validation request and the `Validation` base
  class. The base class wraps each business result in an execution.
- `domain/validation_results.py` owns results, executions, and reports.
- `adapters/persistence/postgresql/` implements PostgreSQL storage; `alembic/` contains schema migrations.
- `domain/criterion.py` defines criterion results and YES/NO/UNKNOWN answers.
- `domain/validations/accessories/leasability/criteria.py` contains the concrete
  criterion classes used by accessory leasability.
- `domain/validation_service.py` runs the supplied validations and aggregates
  their results. Business rejection does not stop the suite; technical failure does.
- `domain/validations/accessories/suite.py` defines which accessory validations
  run and constructs the suite. Web dependencies obtain the service from here.
- Each concrete validation owns its business flow. Leasability selects the
  standard or BAWU async function from the order context. Both use ordinary
  conditionals and directly instantiate the criteria they evaluate; BAWU skips
  the StVZO acceptance check.
- Validation executions retain the submitted product and final business result.

Add new accessory checks under `domain/validations/accessories` and include them
in `suite.py`. A small check can be a single module; use a package when it needs
multiple files. Add another product category only when its validations are needed.
Domain code must not depend on FastAPI or concrete provider clients; adapters and
application assembly connect external implementations to business behavior.
