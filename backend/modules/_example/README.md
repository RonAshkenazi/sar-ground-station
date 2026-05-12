# _example Module

> Reference module — copy this to start a new backend module.

## Purpose

This is a template module showing the standard structure. Copy it:

```bash
cp -r backend/modules/_example backend/modules/my-feature
```

Then rename files and update the README.

## Structure

```
_example/
├── README.md              # This file — describe your module here
├── src/
│   ├── models.*           # Data models / schemas
│   ├── services.*         # Business logic (testable, no framework deps)
│   └── api.*              # API routes / endpoints
└── tests/
    ├── unit/              # Fast tests, no external deps
    │   └── test_services* # Test your business logic
    └── integration/       # Tests with DB, APIs, etc.
```

## API

| Export | Type | Description |
|--------|------|-------------|
| `ExampleModel` | Model | Data structure |
| `ExampleService` | Class/Module | Business logic |
| `example_router` | Router | API endpoints |

## Dependencies

- None (reference module)
