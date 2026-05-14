---
name: mem-search
description: Search claude-mem's persistent cross-session memory database. Use when asked "did we already solve this?", "how did we do X last time?", or to find work from previous sessions. Requires claude-mem running.
---

# Memory Search

> **Requires claude-mem** — Install with `npx claude-mem install` if MCP tools `search`, `timeline`, `get_observations` are not available.

Search past work across all sessions. Simple workflow: search → filter → fetch.

## When to Use

Use when users ask about PREVIOUS sessions (not the current conversation):

- "Did we already fix this?"
- "How did we solve X last time?"
- "What happened last week?"

## 3-Layer Workflow (ALWAYS Follow)

**NEVER fetch full details without filtering first. 10x token savings.**

### Step 1: Search — Get Index with IDs

```
search(query="authentication", limit=20, project="my-project")
```

**Returns:** Table with IDs, timestamps, types, titles (~50-100 tokens/result)

**Parameters:**
- `query` — search term
- `limit` — max results, default 20, max 100
- `project` — project name filter
- `type` — "observations", "sessions", or "prompts"
- `obs_type` — comma-separated: bugfix, feature, decision, discovery, change
- `dateStart` / `dateEnd` — YYYY-MM-DD
- `orderBy` — "date_desc" (default), "date_asc", "relevance"

### Step 2: Timeline — Get Context Around Interesting Results

```
timeline(anchor=11131, depth_before=3, depth_after=3, project="my-project")
```

Or find anchor automatically:

```
timeline(query="authentication", depth_before=3, depth_after=3, project="my-project")
```

### Step 3: Fetch — Get Full Details ONLY for Filtered IDs

Review titles from Step 1 and context from Step 2. Pick relevant IDs. Discard the rest.

```
get_observations(ids=[11131, 10942])
```

**ALWAYS use `get_observations` for 2+ observations — single request vs N requests.**

## Why This Workflow?

- Search index: ~50-100 tokens per result
- Full observation: ~500-1000 tokens each
- **10x token savings** by filtering before fetching

## Knowledge Agents

Want synthesized answers instead of raw records? Use `/knowledge-agent` to build a queryable corpus from your observation history.
