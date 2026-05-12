# Frontend — Domain Rules

> Tier-2 agent rules for the frontend domain.
> These extend the root `AGENTS.md` with frontend-specific guidance.

---

## Scope

Everything under `frontend/` — UI components, pages, styling, client-side logic.

## Owner Tag

`[DEV:frontend]`

## Conventions

1. **Module structure** — each feature lives in its own module under `frontend/modules/`
2. **Components** — reusable UI elements live in the module's `src/components/`
3. **Tests** — component and logic tests in `modules/<name>/tests/`
4. **Styling** — follow the project's design system (see `docs/ui/UI_KIT.md`)

## Module Template

Copy `modules/_example/` to start a new module:

```
modules/my-feature/
├── README.md              # What this module does, components it exports
├── src/
│   ├── components/        # React/Vue/Svelte components
│   ├── hooks.*            # Custom hooks (if React)
│   ├── utils.*            # Module-specific utilities
│   └── index.*            # Public exports
└── tests/
    ├── unit/              # Component + logic tests
    └── integration/       # Full-page / interaction tests
```

## Rules

- Every component MUST have at least one test
- No business logic in components — extract to hooks/utils
- No hardcoded strings — use constants or i18n
- Accessible by default — semantic HTML, ARIA labels, keyboard nav
- Responsive — test at mobile, tablet, and desktop breakpoints
- No inline styles for anything reusable — use the design system
