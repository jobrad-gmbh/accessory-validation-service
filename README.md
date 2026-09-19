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
├── domain/
│   ├── product.py
│   ├── validation.py
│   ├── validation_results.py
│   ├── validation_service.py
│   ├── errors.py
│   └── validations/
│       └── accessories/
│           ├── suite.py
│           └── leasability/
│               ├── validation.py
│               ├── strategies.py
│               └── criteria/
└── shared/
    └── decision_strategies/
```

- `domain/product.py` defines submitted product data, origin, business context,
  and the existing product-resolution contract.
- `domain/validation.py` defines the validation request, common interface, and
  execution helpers. `validation_results.py` owns results, executions, and reports.
- `domain/validation_service.py` runs the supplied validations and aggregates
  their results. Business rejection does not stop the suite; technical failure does.
- `domain/validations/accessories/suite.py` defines which accessory validations
  run and constructs the suite. Web dependencies obtain the service from here.
- Each concrete validation owns its criteria and business strategies. Leasability
  contains both the standard and BAWU strategies.
- `shared/decision_strategies` evaluates decision trees without knowing about
  products or accessory policies. Keep generic evaluation mechanics here and
  business-specific paths alongside their validation.

Add new accessory checks under `domain/validations/accessories` and include them
in `suite.py`. A small check can be a single module; use a package when it needs
multiple files. Add another product category only when its validations are needed.
Domain code must not depend on FastAPI or concrete provider clients; adapters and
application assembly connect external implementations to business behavior.

## LLM adapters

Standalone clients live in `app/adapters/llm`; they are not wired into validations.
No additional SDK dependency is needed. `LiteLLMClient` targets **LiteLLM Proxy**,
not the LiteLLM Python SDK. `OpenAICompatibleClient` targets the Chat Completions
API. Both implement the `LLMClient` protocol for async text generation.

Settings come from explicit constructor values, environment variables, then `.env`.
Use the `LITELLM_`, `OPENAI_`, or `TYPESAFE_` prefixes shown in `.env.example`.
Endpoint and model list are required: there is no local-server or model default.
Timeout defaults to 60 seconds. Temperature and token limit are omitted unless
configured, allowing the provider's defaults. Model names must belong to that endpoint.

Inside an async function:

```python
import httpx
from app.adapters.llm import LiteLLMClient, LiteLLMConfig

async with httpx.AsyncClient() as http:
    client = LiteLLMClient(http)  # Loads LITELLM_* settings.

    # Override any setting when constructing a client:
    custom = LiteLLMClient(http, LiteLLMConfig(
        models=("primary-alias", "backup-alias"),
        temperature=0.2,
        timeout_seconds=20,
    ))  # Endpoint and key still come from the environment.

    # Or override one call without changing the client's defaults:
    response = await client.generate(
        "Describe a bicycle rack.",
        instructions="Keep the answer brief.",
        config=client.config.with_overrides(temperature=0.1, max_tokens=200),
    )
    print(response.text)
```

The caller owns the HTTP client; reuse it over the service's lifetime. Generation
timeout is applied separately to each model attempt.

Models are attempted in order **only when the provider explicitly reports a model
not found**. Exhaustion raises `ModelsNotFoundError` with the attempted names.
Authentication, rate limits, server errors, and timeouts fail immediately; there
are no implicit retries. A generic 404 does not trigger fallback. Invalid, refused,
empty, or incomplete responses raise `LLMResponseError`; timeouts raise
`LLMTimeoutError`. Both inherit from `LLMError`. Provider bodies and prompts are
excluded from error messages.
This adapter returns text; application-specific JSON parsing belongs to its caller.

### Jev / TypeSafe

[Jev's API](https://docs.typesafe.ai/api) evaluates typed questions against state.
It does not document text generation, streaming, temperature, or token-limit
controls. `JevClient` therefore exposes `evaluate()` with its own request and
response types rather than implementing the text-generation protocol. Its config
shares endpoint, credentials, ordered models, and timeout with the other clients.

```python
from app.adapters.llm import JevClient, JevRequest, NoulQuestion

async with httpx.AsyncClient() as http:
    client = JevClient(http)  # Loads TYPESAFE_* settings.
    response = await client.evaluate(JevRequest(
        state={"name": "Fixed rack", "description": "Bolted to the bicycle frame"},
        questions={
            "mounted": NoulQuestion(instructions="Is the accessory fixed to the bicycle?"),
        },
    ))
    print(response.answers["mounted"])
```

`ChoiceQuestion` and `ScoreQuestion` are also supported, including typed answers
and response validation. TypeSafe does not document its missing-model error body.
For now, Jev fallback recognizes only an explicit `error.code=model_not_found`
on HTTP 400/404/422. This conservative recognition is mocked in tests and must be
verified against a real TypeSafe missing-model response before relying on fallback
there. Other errors are surfaced rather than guessed from their text.

Adapter tests use mocked HTTP responses; they need no credentials or network access.
