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

## LLM adapters

Clients live in `app/adapters/llm`. `LiteLLMClient` is wired into accessory
validation and targets **LiteLLM Proxy**, not the LiteLLM Python SDK. No additional
SDK dependency is needed. It implements the `LLMClient` protocol for async text
generation through LiteLLM's chat-completions endpoint.

Settings come from explicit constructor values, environment variables, then `.env`.
Use the `LITELLM_` or `TYPESAFE_` prefixes shown in `.env.example`.
The LiteLLM endpoint and baseline model list are required. Timeout defaults to 60
seconds. Temperature and token limit are omitted unless configured, allowing the
provider's defaults. Model names must belong to that endpoint.

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

The application creates one shared HTTP client, `litellm_client`, and `jev_client`
at startup. The HTTP client is closed at shutdown. A lightweight validation service
is built for each API request using the shared clients. The current accessory-type
criterion receives `litellm_client` through the validation and strategy;
`jev_client` is available for typed evaluation tasks. Generation timeout is applied
separately to each model attempt.

Each criterion call can override the shared defaults without changing other calls:

```python
result = await ExplicitlyNotLeasableAccessoryTypeCriterion(llm_client).evaluate(
    request,
    config=llm_client.config.with_overrides(
        models=("gpt-luna", "glm-5.3"),
        temperature=0.1,
        max_tokens=200,
        timeout_seconds=30,
    ),
)
```

These overrides are made in Python at the criterion call site; they are not fields
in the public API payload. When `config` is omitted, the criterion keeps the shared
client's other parameters and applies its own default models. The explicitly-not-
leasable criterion declares `gpt-luna` and `glm-5.3` in `criteria.py`.

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
