# Accessory Validator

FastAPI service that runs the configured accessory validations and returns one
report containing their business results.

## Run locally

```bash
uv sync --locked
uv run python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

The API documentation is available at <http://127.0.0.1:8000/docs>.

## Validate an accessory

```bash
curl -X POST http://127.0.0.1:8000/api/v1/accessories/validate \
  -H 'Content-Type: application/json' \
  -d '{
    "brand": "Example",
    "model": "Rear rack",
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

## Other endpoints

- `GET /` returns the service name.
- `GET /health` returns service health.

## Development

```bash
uv run python -m pytest
uv run python -m ruff check app tests
uv run python -m mypy app
```

The current leasability criteria return placeholder random answers. The API and
aggregation behavior are ready to exercise while each criterion receives its
real implementation.
