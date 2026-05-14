---
name: smart-explore
description: Token-optimized structural code search using AST parsing. Use instead of reading full files when you need to understand code structure, find functions, or explore efficiently. Requires claude-mem running.
---

# Smart Explore

> **Requires claude-mem** — Install with `npx claude-mem install` if MCP tools `smart_search`, `smart_outline`, `smart_unfold` are not available.

Structural code exploration using AST parsing. **While this skill is active, use smart_search/smart_outline/smart_unfold as your primary tools** instead of Read, Grep, and Glob.

**Core principle:** Index first, fetch on demand. Get a map of the code before loading implementation details.

## Your Next Tool Call

```
smart_search(query="<topic>", path="./src")    -- discover files + symbols across a directory
smart_outline(file_path="<file>")              -- structural skeleton of one file
smart_unfold(file_path="<file>", symbol_name="<name>")  -- full source of one symbol
```

Do NOT run Grep, Glob, or Read to discover files first. `smart_search` walks directories, parses all code files, and returns ranked symbols in one call.

## 3-Layer Workflow

### Step 1: Search — Discover Files and Symbols

```
smart_search(query="shutdown", path="./src", max_results=15)
```

Returns ranked symbols with signatures, line numbers, plus folded file views (~2-6k tokens). This is your discovery tool — no Glob/find pre-scan needed.

**Parameters:**
- `query` — what to search for (function name, concept, class name)
- `path` — root directory (defaults to cwd)
- `max_results` — max matching symbols, default 20, max 50
- `file_pattern` — filter to specific files/paths

### Step 2: Outline — Get File Structure

```
smart_outline(file_path="services/worker-service.ts")
```

Returns complete structural skeleton — all functions, classes, methods, imports (~1-2k tokens per file). **Skip this step** when Step 1's folded views already provide enough structure.

### Step 3: Unfold — See Implementation

Review symbols from Steps 1-2. Pick the ones you need. Unfold only those:

```
smart_unfold(file_path="services/worker-service.ts", symbol_name="shutdown")
```

Returns full source of the specified symbol (~400-2,100 tokens). AST node boundaries guarantee completeness regardless of symbol size.

## When to Use Standard Tools Instead

- **Grep:** Exact string/regex search across files
- **Read:** Small files under ~100 lines, non-code files (JSON, markdown, config)
- **Glob:** File path patterns
- **Explore agent:** Synthesized understanding across 6+ files or cross-file architecture narratives

## Token Economics

| Approach | Tokens | Use Case |
|---|---|---|
| smart_outline | ~1,000-2,000 | "What's in this file?" |
| smart_unfold | ~400-2,100 | "Show me this function" |
| smart_search | ~2,000-6,000 | "Find all X across the codebase" |
| Read (full file) | ~12,000+ | When you truly need everything |

**4-8x savings** on file understanding vs Read. Supports JS/TS, Python, Go, Rust, Ruby, Java, C/C++, Markdown.
