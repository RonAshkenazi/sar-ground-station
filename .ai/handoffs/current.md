# Handoff: Result Analysis — Nearest-Assignment Score

## Requested Role
[DEV:backend] + [DEV:frontend]

## Goal

When the ratio gate filters out ambiguous GTs, the strict score can collapse to 0 even when the localization is actually reasonable. Add a parallel **nearest-assignment score** that bypasses the ratio gate — always assigns each GT to its nearest cluster within `max_match_dist_m` — and return it alongside the strict score. The frontend shows it when ambiguous GTs exist, so the researcher can distinguish "confident match" quality from "did the system find the targets at all."

## Context

Current flow in `engine.py`:
- A `cost` matrix is built. GTs that fail the ratio gate get `_GATE_INF` in every cell → excluded from assignment.
- `_linear_sum_assignment(cost)` runs on this gated matrix → `primary_pairs` → strict `score`.
- Ambiguous GTs appear in `ambiguous_gts[]` but contribute nothing to the score.

With dense cluster outputs (102 clusters, 3 GTs, all `d2/d1 ≈ 1.05–1.26`), all three GTs are ambiguous at `ratio_gate=1.2` and `score.total = 0` even though every GT is within 40–90m of its nearest cluster.

The fix: second pass with a `cost_nearest` matrix that ignores the ratio gate. Every GT within `max_match_dist_m` participates. Run the same assignment algorithm. Compute a parallel `nearest_score`. Return it in the response. **Do not change the strict `score` or any existing fields.**

---

## Backend change — `backend/app/modules/result_analysis/engine.py`

### Where to insert

After line 73 (`primary_pairs = _linear_sum_assignment(cost)`) and the existing matches/scoring block, add the nearest-assignment second pass. Insert it **before** the `return` statement.

### New code to add (inside `evaluate`, after the existing score computation block ending at line 207)

```python
    # --- Nearest-assignment score (no ratio gate) ---
    cost_nearest = [[_GATE_INF] * n_gt for _ in range(n_pred)]
    for j in range(n_gt):
        if j in far_fn_gt_indices:
            continue
        sorted_by_dist = sorted(range(n_pred), key=lambda i: dist_m[i][j])
        nearest_i = sorted_by_dist[0]
        if dist_m[nearest_i][j] <= max_match_dist_m:
            cost_nearest[nearest_i][j] = dist_m[nearest_i][j]

    nearest_pairs = _linear_sum_assignment(cost_nearest)
    nearest_errors = [dist_m[i][j] for i, j in nearest_pairs]
    nearest_covered = sum(
        1 for i, j in nearest_pairs
        if dist_m[i][j] <= max(float(preds[i].get("radius_m") or 0.0), d_free_m)
    )
    nearest_coverage = nearest_covered / max(len(nearest_pairs), 1) if nearest_pairs else 0.0
    nearest_median_error = statistics.median(nearest_errors) if nearest_errors else None
    nearest_recall = len(nearest_pairs) / n_gt if n_gt > 0 else 0.0

    ns_containment = nearest_coverage
    if nearest_median_error is None:
        ns_distance = 0.0
    elif nearest_median_error <= d_free_m:
        ns_distance = 1.0
    else:
        ns_distance = max(0.0, 1.0 - ((nearest_median_error - d_free_m) / r_normalize_m) ** 2)
    ns_count = nearest_recall
    ns_total = w_containment * ns_containment + w_distance * ns_distance + w_count * ns_count + w_radius * s_radius
```

### Add `nearest_score` to the return dict

Inside the existing `return { ... }` block (after the `"score": {...}` entry), add:

```python
        "nearest_score": {
            "total": round(ns_total, 4),
            "containment": round(ns_containment, 4),
            "distance": round(ns_distance, 4),
            "count": round(ns_count, 4),
            "radius": round(s_radius, 4),
            "n_matches": len(nearest_pairs),
        },
```

`s_radius` is reused because the radius score depends on cluster radii, not on GT assignment.

---

## Frontend changes

### 1. `frontend/src/api/sessions.ts` — extend `EvaluationResult`

Add `nearest_score` as an optional field to the `EvaluationResult` interface (after the `score` block, around line 319):

```typescript
  nearest_score?: {
    total: number
    containment: number
    distance: number
    count: number
    radius: number
    n_matches: number
  }
```

### 2. `frontend/src/pages/ResultAnalysisPage.tsx` — show nearest score

In the score panel (lines 708–734), after the closing `</div>` of the `score-grid` and after the `reliability-note` paragraph, add a secondary score block that appears only when there are ambiguous GTs and a nearest score exists:

```tsx
{evalResult.nearest_score && (evalResult.ambiguous_gts?.length ?? 0) > 0 && (
  <div className="nearest-score-block">
    <div className="nearest-score-header">
      Nearest-assignment score
      <HelpTip text="Score computed by ignoring the ratio gate — each GT is always assigned to its nearest cluster within max match distance. Use this when ambiguous GTs are dragging the strict score to zero." />
    </div>
    <div className="nearest-score-total">{(evalResult.nearest_score.total * 100).toFixed(1)}%</div>
    <div className="score-grid">
      <ScoreItem label="Containment" value={evalResult.nearest_score.containment} />
      <ScoreItem label="Distance" value={evalResult.nearest_score.distance} />
      <ScoreItem label="Count" value={evalResult.nearest_score.count} />
      <ScoreItem label="Radius" value={evalResult.nearest_score.radius} />
    </div>
    <div className="metric-row">
      <span>Nearest matches</span>
      <span>{evalResult.nearest_score.n_matches} / {evalResult.n_gt}</span>
    </div>
  </div>
)}
```

### 3. CSS — `frontend/src/pages/ResultAnalysisPage.css`

Add styles for the new block. Keep it visually subordinate to the strict score — same layout, muted colors:

```css
.nearest-score-block {
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px dashed var(--color-border);
}

.nearest-score-header {
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--color-text-muted);
  margin-bottom: 4px;
  display: flex;
  align-items: center;
  gap: 4px;
}

.nearest-score-total {
  font-size: 22px;
  font-weight: 600;
  color: var(--color-text-muted);
  margin-bottom: 6px;
}
```

---

## Acceptance criteria

- [ ] `evaluate()` always returns `nearest_score` in the response, with `n_matches`, `total`, and four sub-scores.
- [ ] When all GTs are ambiguous (strict `score.total = 0`), `nearest_score.total` is non-zero if GTs are within `max_match_dist_m` of any cluster.
- [ ] When no GTs are ambiguous, `nearest_score.total ≈ score.total` (same assignment result).
- [ ] Frontend shows the nearest-score block only when `ambiguous_gts.length > 0`.
- [ ] Strict `score` is unchanged — no existing fields modified or removed.
- [ ] TypeScript compiles with no errors.

## Out of scope

- Do not change the ratio gate logic, the strict score, or any existing response fields.
- Do not add nearest-score matches to the map overlays.
- Do not expose nearest-score as a rerun parameter.
