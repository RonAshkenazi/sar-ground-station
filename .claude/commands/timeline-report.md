---
name: timeline-report
description: Generate a narrative report analyzing a project's entire development history from claude-mem's timeline. Use when asked for a timeline report, project history analysis, or development journey. Requires claude-mem running.
---

# Timeline Report

> **Requires claude-mem** — Install with `npx claude-mem install` and ensure the worker is running.

Generate a comprehensive narrative analysis of a project's entire development history using claude-mem's persistent memory timeline.

## Resolve Worker Port (do once, reuse)

```bash
WORKER_PORT="${CLAUDE_MEM_WORKER_PORT:-$(node -e "const fs=require('fs'),p=require('path'),os=require('os');const uid=(typeof process.getuid==='function'?process.getuid():77);const fallback=String(37700+(uid%100));try{const s=JSON.parse(fs.readFileSync(p.join(os.homedir(),'.claude-mem','settings.json'),'utf-8'));process.stdout.write(String(s.CLAUDE_MEM_WORKER_PORT||fallback));}catch{process.stdout.write(fallback);}" 2>/dev/null)}"
```

## Workflow

### Step 1: Determine Project Name

Use the current directory basename, or ask the user. For git worktrees, use the parent repo name:

```bash
git_common_dir=$(git rev-parse --git-common-dir 2>/dev/null)
git_dir=$(git rev-parse --git-dir 2>/dev/null)
if [ "$git_dir" != "$git_common_dir" ]; then
  parent_project=$(basename "$(dirname "$git_common_dir")")
else
  parent_project=$(basename "$PWD")
fi
echo "$parent_project"
```

### Step 2: Fetch the Full Timeline

```bash
curl -s "http://localhost:${WORKER_PORT}/api/context/inject?project=PROJECT_NAME&full=true"
```

### Step 3: Estimate Token Count and Confirm

Estimate ~1 token per 4 characters. Report to user and wait for confirmation if > 100K tokens.

### Step 4: Analyze with a Subagent

Deploy an Agent with the full timeline. The report must cover:

1. **Project Genesis** — first commits, initial vision, founding decisions
2. **Architectural Evolution** — major pivots and why they happened
3. **Key Breakthroughs** — "aha" moments when hard problems were solved
4. **Work Patterns** — debugging cycles, feature sprints, refactoring phases
5. **Technical Debt** — shortcuts taken and when paid back
6. **Challenges and Debugging Sagas** — hardest problems, multi-session efforts
7. **Memory and Continuity** — how recalled context saved time
8. **Token Economics & Memory ROI** — quantitative analysis using SQLite queries on `~/.claude-mem/claude-mem.db`
9. **Timeline Statistics** — date range, total observations, breakdown by type
10. **Lessons and Meta-Observations** — patterns visible only from the full history

Writing style: technical narrative, not bullet lists. Use observation IDs and timestamps. Connect events across time. 3,000–6,000 words.

### Step 5: Save the Report

Default: `./journey-into-PROJECT_NAME.md`

## Error Handling

- **Empty timeline:** Check project name with `curl -s "http://localhost:${WORKER_PORT}/api/search?query=*&limit=1"`
- **Worker not running:** Start with your usual method or check `ps aux | grep worker-service`
