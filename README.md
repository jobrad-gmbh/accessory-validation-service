# Accessory Validator

Service scaffold for classifying bicycle accessories as leasable or not
leasable. It is adapted from the JobRad Python service template and intentionally
contains no implemented classification policy or external service connection.

## Project structure

```text
app/
├── main.py
├── adapters/
│   ├── web/
│   │   ├── accessory_routes.py
│   │   ├── dependencies.py
│   │   ├── exceptions.py
│   │   ├── schemas.py
│   │   └── system_routes.py
│   ├── research/
│   │   └── searxng.py
│   └── llm/
│       └── client.py
├── config/
│   ├── logging.py
│   └── settings.py
├── domain/
│   ├── accessory_classifier.py
│   ├── entities.py
│   ├── ports.py
│   ├── rules/
│   │   ├── base.py
│   │   ├── resolver.py
│   │   ├── permanently_attached.py
│   │   ├── traffic_law.py
│   │   ├── excluded_category.py
│   │   └── bawu.py
│   └── decisions/
│       ├── base.py
│       ├── resolver.py
│       ├── default.py
│       └── bawu.py
└── tests/
    ├── conftest.py
    └── integration/
```

This keeps the template’s hexagonal organization:

- `domain/` owns business-facing entities, ports, rules, decision strategies,
  and the classifier service boundary.
- `adapters/web/` owns FastAPI routes and schemas.
- `adapters/research/` and `adapters/llm/` reserve the external integration
  points without implementing network calls.
- `config/` retains the template’s environment settings and logging setup.
- Tests override the classifier dependency with a mock, so the proposed HTTP
  contract can be exercised before business logic exists.

## Current scope

The scaffold defines:

- `AccessoryClassifier`
- `ClassificationContext`
- rule and decision strategy base classes
- default and BaWü extension points
- SearXNG and LLM adapter placeholders
- `POST /api/v1/accessories/classify`
- template-style root, health, validation errors, CI, Docker, Nomad, and
  Backstage files

All unimplemented application and integration methods fail explicitly with
`NotImplementedError`. No leasing decision or external HTTP request is made by
the scaffold.

## Development

```bash
make setup
make start
make test
make lint
```
