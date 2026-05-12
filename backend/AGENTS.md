# Backend — Domain Rules

> Tier-2 agent rules for the backend domain.
> These extend the root `AGENTS.md` with backend-specific guidance.

---

## Scope

Everything under `backend/` — API endpoints, business logic, data models, services.

## Owner Tag

`[DEV:backend]`

## Conventions

1. **Module structure** — each feature lives in its own module under `backend/modules/`
2. **Public API** — export only what's needed via the module's `__init__.py` or `index.ts`
3. **No cross-module imports** — modules talk to each other through shared interfaces, not direct imports
4. **Tests live with the module** — unit tests in `modules/<name>/tests/unit/`, integration in `tests/integration/`

## Module Template

Copy `modules/_example/` to start a new module:

```
modules/my-feature/
├── README.md          # What this module does, its API, dependencies
├── src/
│   ├── models.*       # Data models / schemas
│   ├── services.*     # Business logic
│   └── api.*          # API endpoints / routes
└── tests/
    ├── unit/          # Fast, isolated tests
    └── integration/   # Tests with external dependencies
```

## Rules

- Every module MUST have a `README.md` explaining what it does
- Every service function MUST have at least one unit test
- API endpoints MUST validate input
- No hardcoded secrets — use environment variables
- No direct database queries in route handlers — use service layer
