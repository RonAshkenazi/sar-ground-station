# Codex Handoff — Save Session Wiring Fixes (MOD-013 follow-up)

## Requested Role

[DEV:frontend]

## Goal

Three small but critical fixes to make Save Session actually work end-to-end:

1. **Enable the Save button after localization** — refresh `SessionContext` when localization completes so `Header.tsx` sees `active_localization` and enables the button.
2. **Show previous result after Resume** — when `LocalizationPage` loads and `sessionState.current_localization_result` is already populated (from a resume), pre-fill the `result` state so the map and cluster table appear immediately without re-running.
3. **Confirm save to the user** — show a brief success banner/toast after Save Session completes.

No backend changes needed — the backend is correct.

---

## Fix 1 — Refresh SessionContext after localization succeeds

**File:** `frontend/src/pages/LocalizationPage.tsx`

**Problem:** `Header.tsx` gates the Save Session button on `session?.active_localization`. The backend sets this after a successful run, but `SessionContext.session` is never refreshed, so the header always sees `null`.

**Fix:** `SessionContext` already exposes `refreshSession()`. Import it and call it (fire-and-forget) after the polling success case.

Change the import:
```tsx
const { session, refreshSession } = useSession()   // add refreshSession
```

In the polling `useEffect`, after `setExecution(next)` on success:
```tsx
if (next.status === 'success') {
  setResult(next.result_metadata as unknown as LocalizationRunResult)
  setExecution(next)
  window.clearInterval(interval)
  void refreshSession()   // ← add this line
}
```

`refreshSession()` calls `GET /api/sessions/{id}/state` and updates the context — `Header.tsx` will then see `active_localization` and enable the Save button.

---

## Fix 2 — Pre-fill result from saved state on page load

**File:** `frontend/src/pages/LocalizationPage.tsx`

**Problem:** After Resume, `SessionContext.session` has `current_localization_result` populated, and after the page-load `useEffect` fetches session state, `sessionState.current_localization_result` is also populated. But `result` state is initialised to `null` and never reads from it. The map is blank.

**Fix:** In the first `useEffect` (the one that calls `getInventory` + `getSessionState`), after setting session state, also initialise `result` from the saved localization data if present:

```tsx
Promise.all([getInventory(session.session_id), getSessionState(session.session_id)])
  .then(([nextInventory, nextState]) => {
    setInventory(nextInventory)
    setSessionState(nextState)
    // Pre-fill result from a resumed session
    const saved = nextState?.current_localization_result
    if (saved) {
      setResult(saved as unknown as LocalizationRunResult)
    }
  })
  .catch((err: unknown) => setError(String(err)))
```

This makes Resume land on the Localization page with the map immediately showing the previous result and the cluster table populated.

---

## Fix 3 — Confirm save to the user

**File:** `frontend/src/components/layout/Header.tsx`

**Problem:** After clicking Save Session, the button briefly says "Saving..." then reverts with no confirmation. The user has no idea if the save worked.

**Fix:** Add a `saved` state that shows briefly after a successful save.

```tsx
const [saving, setSaving] = useState(false)
const [saved, setSaved] = useState(false)

async function handleSave() {
  if (!session?.session_id) return
  setSaving(true)
  setSaved(false)
  try {
    await saveSession(session.session_id)
    setSaved(true)
    setTimeout(() => setSaved(false), 3000)   // clear after 3s
  } finally {
    setSaving(false)
  }
}
```

Change the button label:
```tsx
{saving ? 'Saving...' : saved ? 'Saved ✓' : 'Save Session'}
```

No new CSS needed — the existing `btn-save-session` style applies.

---

## Tests to run

```bash
cd frontend && npm run build
```

No backend changes, no new unit tests needed for these wiring fixes.

After the build passes, run the demo in headed mode to verify end-to-end:

```bash
npx playwright test tests/e2e/demo.spec.ts --config=playwright.demo.config.ts --reporter=list
```

The demo should:
1. Complete the full pipeline
2. After localization, the Save Session button in the header should become enabled (not grey)
3. Click Save Session — button briefly shows "Saving..." then "Saved ✓"
4. Reload the page / navigate away and back
5. Session Start should show the saved session in the Resume table
6. Click Resume — Localization page opens with the previous result already on the map

If the demo script does not yet exercise Save and Resume, extend it with those steps and take a final screenshot `demo_result_v3.png`.

---

## Scope

May only change:
- `frontend/src/pages/LocalizationPage.tsx`
- `frontend/src/components/layout/Header.tsx`
- `tests/e2e/demo.spec.ts` (add save + resume verification steps)

Must NOT change:
- Any backend files
- Any CSS files
- `SessionContext.tsx` — the existing `refreshSession()` is correct, just use it

---

## Acceptance Criteria

- [ ] Save Session button is enabled (not greyed) immediately after localization result appears
- [ ] Clicking Save Session shows "Saving..." then "Saved ✓" for ~3 seconds
- [ ] After Resume from Session Start, Localization page shows the previous result on the map without re-running
- [ ] Cluster table is populated after Resume
- [ ] Map flies to previous result bounds after Resume (SetViewOnResult fires because `result` is now set)
- [ ] `npm run build` passes cleanly
