# Codex Handoff — Result Analysis: Fix Ratio Gate Default + Add-from-Map UX

## Requested Role

[DEV:frontend] + [DEV:backend]

---

## Context

Codex QA/Researcher diagnosed two confirmed bugs in the Result Analysis page (see `.ai/codex_result.md`):

1. **Score = 0** — caused by `ratio_gate` default of `2.0`, which in practice classifies every GT as ambiguous in dense cluster outputs (102 predictions, d2/d1 ratios of 1.05–1.26). Changing the default to `1.2` produces matches and a non-zero score.

2. **"Add from map" is one-shot** — `handleAddGt()` calls `setAddingGt(false)` after the first click, so a second GT click does nothing. The founder believed add-mode was persistent. This explains why only one GT appeared on the map at a time.

Both backend and frontend multi-GT storage and evaluation are verified correct — no changes needed there.

---

## Fix 1 — Backend: Lower ratio_gate default to 1.2

**File:** `backend/app/modules/result_analysis/engine.py`

Change line:
```python
_RA_RATIO_GATE: float = 2.0
```
To:
```python
_RA_RATIO_GATE: float = 1.2
```

No other changes to `engine.py`.

---

## Fix 2 — Frontend: Lower ratio_gate UI default to 1.2

**File:** `frontend/src/pages/ResultAnalysisPage.tsx`

In the `evalParams` state initializer (around line 41–49), change:
```typescript
ratio_gate: 2.0,
```
To:
```typescript
ratio_gate: 1.2,
```

---

## Fix 3 — Frontend: Make "Add from map" persistent (toggle, not one-shot)

**File:** `frontend/src/pages/ResultAnalysisPage.tsx`

**Current behavior:** `handleAddGt()` calls `setAddingGt(false)` after each successful click (line ~140). This exits add-mode after the first point.

**Required behavior:** Add-mode stays active until the user explicitly clicks the "Add from map" button again to toggle it off. Each map click adds a GT point and keeps the mode on. The user dismisses add-mode by clicking the button a second time.

**Change `handleAddGt()`** — remove `setAddingGt(false)` from the success path. Keep it only in the `finally` block if an error occurs, or remove it entirely from `handleAddGt`. The toggle button already handles dismissal via `onClick={() => setAddingGt((value) => !value)`.

Before (approximate):
```typescript
async function handleAddGt(point: { lat: number; lon: number }) {
  if (!session?.session_id) return
  setLoading(true)
  setError(null)
  try {
    await addGtPoint(session.session_id, point.lat, point.lon)
    await loadState()
    setAddingGt(false)   // <-- remove this line
  } catch (err: unknown) {
    setError(String(err))
  } finally {
    setLoading(false)
  }
}
```

After:
```typescript
async function handleAddGt(point: { lat: number; lon: number }) {
  if (!session?.session_id) return
  setLoading(true)
  setError(null)
  try {
    await addGtPoint(session.session_id, point.lat, point.lon)
    await loadState()
  } catch (err: unknown) {
    setError(String(err))
  } finally {
    setLoading(false)
  }
}
```

**Also update the button label** to make the active state clear. The current button text switches between `'Click on map...'` and `'Add from map'`. Keep this — it is already correct UX for a toggle. No label change needed.

---

## Fix 4 — Frontend: Add helper text below the ratio_gate input

**File:** `frontend/src/pages/ResultAnalysisPage.tsx`

Below the existing ratio_gate input block (around line 333), add a small hint element:

```tsx
<div className="eval-param-row">
  <label>Ratio gate</label>
  <input
    type="number"
    step="0.1"
    min="1.0"
    value={evalParams.ratio_gate ?? 1.2}
    onChange={(event) => setEvalParams((previous) => ({ ...previous, ratio_gate: Number(event.target.value) }))}
  />
</div>
<p className="eval-param-hint">
  Lower = more permissive. 1.0 = always match nearest. 2.0 = strict (nearest must be 2× closer than second-nearest).
</p>
```

Add the CSS class `.eval-param-hint` to `ResultAnalysisPage.css`:
```css
.eval-param-hint {
  font-size: 0.72rem;
  color: var(--text-muted, #888);
  margin: -4px 0 8px 0;
  line-height: 1.4;
}
```

---

## Out of Scope

- Do not change the score formula weights (RA-04 through RA-07 are still TBD per spec)
- Do not add a dual "strict + nearest-assignment" score — that is a future founder decision
- Do not touch `gt_store.py`, backend evaluation logic, or any other module
- Do not modify anything outside `engine.py`, `ResultAnalysisPage.tsx`, and `ResultAnalysisPage.css`

---

## Tests to Run

```powershell
cd backend; pytest tests/ -k "result_analysis" -v
cd frontend; npm test
```

If no existing result_analysis tests exist, note that in the result — do not write new tests in this pass.

After implementing, verify manually:
1. Start backend + frontend
2. Load a session that has a localization result
3. Click "Add from map" — mode activates
4. Click 3 different map positions — all 3 GT rows should appear in the list without toggling the button
5. Click "Add from map" again — mode deactivates
6. Run Evaluation with default `ratio_gate = 1.2` — score should be non-zero for a reasonable session
7. Confirm the hint text appears below the ratio_gate input

---

## Acceptance Criteria

- [ ] `_RA_RATIO_GATE` in `engine.py` is `1.2`
- [ ] `evalParams.ratio_gate` default in `ResultAnalysisPage.tsx` is `1.2`
- [ ] `handleAddGt()` no longer calls `setAddingGt(false)` on success — add-mode persists until manually toggled off
- [ ] Hint text visible below the ratio_gate input field
- [ ] Backend tests pass (or absence of result_analysis tests reported)
- [ ] Frontend tests pass
- [ ] Manual verification of multi-GT add flow completed

---

## Constraints

- Do not invent TBD spec values
- Do not run `git commit`
- Do not modify any other module
- Preserve all existing evalParams fields and their UI inputs

## Founder Decisions Needed

None — all changes are confirmed by Codex QA/Researcher findings. The `1.2` default is the Researcher recommendation and founder approved direction.
