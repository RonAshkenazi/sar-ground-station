---
name: knowledge-agent
description: Build and query AI-powered knowledge bases from claude-mem observations. Use to create focused "brains" from observation history or ask questions about past work patterns. Requires claude-mem running.
---

# Knowledge Agent

> **Requires claude-mem** — Install with `npx claude-mem install` if MCP tools `build_corpus`, `prime_corpus`, `query_corpus` are not available.

Build and query AI-powered knowledge bases from claude-mem observations.

## What Are Knowledge Agents?

Knowledge agents are filtered corpora of observations compiled into a conversational AI session. Build a corpus from your observation history, prime it, then ask questions conversationally.

Think of them as custom "brains": "everything about the Re-ID algorithm", "all decisions from Sprint 02", "all enrichment bug fixes".

## Workflow

### Step 1: Build a corpus

```
build_corpus name="reid-expertise" description="Everything about the Re-ID algorithm" project="test" concepts="reid,bleach" limit=500
```

Filter options:
- `project` — filter by project name
- `types` — comma-separated: decision, bugfix, feature, refactor, discovery, change
- `concepts` — comma-separated concept tags
- `files` — comma-separated file paths (prefix match)
- `query` — semantic search query
- `dateStart` / `dateEnd` — ISO date range
- `limit` — max observations (default 500)

### Step 2: Prime the corpus

```
prime_corpus name="reid-expertise"
```

Creates an AI session loaded with all the corpus knowledge.

### Step 3: Query

```
query_corpus name="reid-expertise" question="What constants did we set for sequence gap threshold and why?"
```

Follow-up questions maintain context.

### Step 4: Maintain

- `list_corpora` — show all corpora with stats
- `rebuild_corpus name="..."` — refresh with new observations
- `reprime_corpus name="..."` — clear Q&A context and reload

## Tips

- **Focused corpora work best** — "Bleach Re-ID algorithm" beats "everything ever"
- **Prime once, query many times** — the session persists across queries
- **Rebuild to update** — when new observations are added, rebuild then reprime
