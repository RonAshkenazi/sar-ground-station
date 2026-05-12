# Sprints

> Each sprint gets its own folder: `sprint_01/`, `sprint_02/`, etc.

## Sprint Folder Structure

```
sprint_XX/
├── sprint_XX_index.md         # Sprint goals, status, timeline
├── todo/
│   └── sprint_XX_todo.md      # Task list with acceptance criteria
├── reports/
│   └── sprint_XX_report.md    # What was delivered, what wasn't
└── reviews/
    └── sprint_XX_review.md    # Retrospective, lessons learned
```

## Workflow

1. **CTO** creates the sprint folder and fills in `sprint_XX_index.md`
2. **CTO** breaks PRD features into tasks in `todo/sprint_XX_todo.md`
3. **DEV** works through tasks, checking them off
4. **QA** verifies completed tasks
5. **DEV/QA** write the sprint report
6. **Team** does a brief review / retro

## Naming Convention

- Sprint numbers are zero-padded: `sprint_01`, `sprint_02`, ...
- Files are prefixed with the sprint ID
- One sprint folder per sprint (don't reuse)
