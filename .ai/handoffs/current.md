# Codex Handoff — Sprint 03: Confidence Tier Visibility + Pipeline QA

## Requested Role

[SUPERVISOR → spawn 3 parallel workers]

## Instructions for Codex Supervisor

**Do not implement anything yourself.** Spawn three sub-agents in parallel:

- **Worker A** — Backend (`[DEV:backend]` + `[DEV:algo]`)
- **Worker B** — Frontend (`[DEV:frontend]`)
- **Worker C** — QA pipeline validation (`[QA]`) — runs independently, no dependency on A or B

Worker B must treat all new backend fields as optional (`?.`) to stay unblocked.
Worker C writes and runs a Playwright spec against the **current** code. It does not need to wait for A or B.

After all workers complete, run:
```bash
cd backend && python -m pytest tests/unit/ -x -q
cd frontend && npm.cmd run build
```

Report results in `.ai/codex_result.md`.

---

# WORKER A — Backend

## Files to change

- `backend/app/modules/reid/engine.py`
- `backend/tests/unit/test_skeleton.py`

## Must NOT touch

- Any frontend file
- Any other backend file

---

## Background

The Re-ID engine already computes a per-cluster confidence tier (`"high"` / `"medium"` / `"low"`) based on the best Bleach association score for that cluster. This is computed at line ~107 in `run_reid`:

```python
confidence_by_cluster = _cluster_confidence(cluster_by_unit, accepted)
```

`_confidence_tier` maps scores as follows:
- `score >= 0.75` → `"high"`
- `score >= 0.60` → `"medium"`
- `score < 0.60` → `"low"`

Singleton clusters (those in `singleton_cluster_ids`) are already mapped to `"noise"` in the output CSV. They must be excluded from `cluster_confidence`.

Static clusters have `cluster_id = src_mac` and `cluster_type = "static"`. They are not in `confidence_by_cluster` at all — that is fine and expected.

---

## Task A1 — Add `cluster_confidence` to `run_reid` return dict

**File:** `backend/app/modules/reid/engine.py`

In the `run_reid` return dict (currently starting at `return {`), add one new field after `"noise_cluster_count"`:

```python
"cluster_confidence": {
    str(cluster_id): tier
    for cluster_id, tier in confidence_by_cluster.items()
    if cluster_id not in singleton_cluster_ids
},
```

This maps string cluster IDs (e.g. `"1"`, `"2"`) — matching the `cluster_id` values written to the REID CSV and used by the localization engine — to their confidence tier.

**Important:** `singleton_cluster_ids` is defined above the return statement in `run_reid`. The filter ensures noise clusters are excluded.

The result should look like:
```python
{
    "reid_csv_path": "...",
    "total_rows": 1000,
    "static_cluster_count": 45,
    "dynamic_cluster_count": 12,
    "unique_dynamic_mac_count": 20,
    "noise_cluster_count": 8,
    "cluster_confidence": {
        "1": "high",
        "2": "medium",
        "3": "low",
        ...
    },
    "warnings": [],
}
```

---

## Task A2 — Unit test

**File:** `backend/tests/unit/test_skeleton.py`

Add the following test after `test_reid_unique_dynamic_mac_count`:

```python
def test_reid_cluster_confidence_in_result(tmp_path) -> None:
    """cluster_confidence maps non-noise dynamic cluster IDs to tier strings."""
    from app.modules.reid.engine import run_reid

    # Write a minimal ENRICHED CSV with 2 randomized MACs (LAA bit set),
    # each with enough rows to be non-singleton (_REID_MIN_ROWS_SINGLETON = 5).
    # Use the same CSV writing pattern as test_reid_unique_dynamic_mac_count.
    csv_path = tmp_path / "scan_ENRICHED.csv"
    rows = []
    base_time = 1_700_000_000.0
    for i in range(6):
        rows.append({
            "timestamp_utc": str(base_time + i),
            "src_mac": "02:aa:bb:cc:dd:01",  # LAA bit = randomized
            "rssi_dbm": "-60",
            "gps_lat": "32.0",
            "gps_lon": "34.0",
            "frame_type": "probe",
        })
    for i in range(6):
        rows.append({
            "timestamp_utc": str(base_time + 100 + i),
            "src_mac": "02:aa:bb:cc:dd:02",  # different randomized MAC
            "rssi_dbm": "-65",
            "gps_lat": "32.001",
            "gps_lon": "34.001",
            "frame_type": "probe",
        })
    import csv as csv_mod
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv_mod.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    result = run_reid(csv_path, protocol="wifi")

    assert "cluster_confidence" in result
    cc = result["cluster_confidence"]
    # Should have entries for dynamic non-noise clusters (those with >= 5 rows become singletons
    # unless they associate — either way non-noise clusters must appear)
    for cluster_id, tier in cc.items():
        assert tier in ("high", "medium", "low"), f"Unexpected tier {tier!r} for cluster {cluster_id}"
        assert cluster_id != "noise", "Noise clusters must not appear in cluster_confidence"
```

---

## Acceptance (Worker A)

- [ ] `cluster_confidence` in `run_reid` return dict
- [ ] Only non-noise dynamic cluster IDs present (no `"noise"` key, no static MAC keys)
- [ ] Values are `"high"`, `"medium"`, or `"low"` only
- [ ] `python -m pytest tests/unit/ -x -q` passes

---

---

# WORKER B — Frontend

## Files to change

- `frontend/src/types/index.ts`
- `frontend/src/api/sessions.ts`
- `frontend/src/pages/LocalizationPage.tsx`
- `frontend/src/pages/LocalizationPage.css`
- `frontend/src/pages/ResultAnalysisPage.tsx`
- `frontend/src/pages/ResultAnalysisPage.css`

## Must NOT touch

- Any backend file
- Any other frontend file

---

## Task B1 — Add `active_reid` to `SessionState` type

**File:** `frontend/src/types/index.ts`

`SessionState` currently has `active_reid_artifact: string | null` (the file path) but no typed object for the quality result. Add:

```typescript
active_reid?: {
  reid_csv_path?: string
  quality?: {
    cluster_confidence?: Record<string, 'high' | 'medium' | 'low'>
  }
} | null
```

---

## Task B2 — Add `cluster_confidence` to `ReIdQuality` interface

**File:** `frontend/src/api/sessions.ts`

In the `ReIdQuality` interface, add:

```typescript
cluster_confidence?: Record<string, 'high' | 'medium' | 'low'>
```

---

## Task B3 — Add confidence badge to Localization cluster table

**File:** `frontend/src/pages/LocalizationPage.tsx`

### Lookup helper

Add a small helper near the top of the component (after the state declarations):

```tsx
function confidenceBadge(tier: string | undefined): React.ReactNode {
  if (!tier) return null
  const cls = tier === 'high' ? 'conf-high' : tier === 'medium' ? 'conf-medium' : 'conf-low'
  return <span className={`conf-badge ${cls}`}>{tier}</span>
}
```

### Table header

In the cluster summary table `<thead>`, add a column after the existing `Radius (m)` column:

```tsx
<th>Confidence</th>
```

### Table cell

In the corresponding `<td>` row for each cluster, add:

```tsx
<td>
  {cluster.cluster_type === 'static'
    ? <span className="conf-badge conf-static">static</span>
    : confidenceBadge(session?.active_reid?.quality?.cluster_confidence?.[cluster.cluster_id])}
</td>
```

---

## Task B4 — Add confidence badge to Result Analysis cluster sidebar

**File:** `frontend/src/pages/ResultAnalysisPage.tsx`

In the cluster visibility list in the left sidebar, add a confidence badge next to each cluster's swatch and checkbox. Use the same `confidenceBadge` helper (copy it into ResultAnalysisPage.tsx or move it to a shared location if one exists — if not, just copy it).

```tsx
{confidenceBadge(session?.active_reid?.quality?.cluster_confidence?.[cluster.cluster_id])}
```

Show nothing for static clusters (their cluster_id is a MAC address and won't be in `cluster_confidence`).

---

## Task B5 — CSS for confidence badges

**File:** `frontend/src/pages/LocalizationPage.css` and `frontend/src/pages/ResultAnalysisPage.css`

Add to both files:

```css
.conf-badge {
  border-radius: 3px;
  font-size: 0.7rem;
  font-weight: 600;
  letter-spacing: 0.02em;
  padding: 1px 5px;
  text-transform: uppercase;
}
.conf-high   { background: #166534; color: #bbf7d0; }
.conf-medium { background: #854d0e; color: #fef9c3; }
.conf-low    { background: #7f1d1d; color: #fecaca; }
.conf-static { background: #1e3a5f; color: #bfdbfe; }
```

---

## Acceptance (Worker B)

- [ ] `SessionState.active_reid.quality.cluster_confidence` typed
- [ ] `ReIdQuality.cluster_confidence` typed
- [ ] Localization cluster table shows confidence badge per dynamic cluster
- [ ] Static clusters show a "static" badge in neutral blue
- [ ] Result Analysis cluster sidebar shows confidence badge
- [ ] No TypeScript errors — `npm.cmd run build` passes

---

---

---

# WORKER C — QA Pipeline Validation (Headed Chromium)

## Files to create

- `tests/e2e/validation_19_1.spec.ts`

## Must NOT touch

- Any backend file
- Any frontend file
- Any other test file

---

## Context

You are running a live end-to-end validation of the full pipeline on real scan data.
The goal is to verify that every stage works correctly on field data, observe the
confidence tiers introduced this sprint, and evaluate localization quality against
a GPS ground-truth reference.

**Run mode:** headed Chromium with slow motion so the founder can watch.

**Scan folder:** `scan - field test 1 - 19.1`
**Calibration CSV:** `scan_2026-01-19_11-14-13Z-calic_search1.csv`
**Calibration MAC:** `2c:59:8a:58:95:c1`
**Main scan CSV:** `scan_2026-01-19_11-20-58Z-test-circle2.csv`
**GT reference CSV:** `runtime/DATA/scan - field test 1 - 19.1/scan_2026-01-19_11-17-03Z-GPS.csv`

The GT reference CSV is a drone GPS track with columns `gps_lat` and `gps_lon`.
Its mean position is the approximate center of where the target device was located.

---

## Task C1 — Read GPS.csv and compute mean GT coordinates

Before writing the spec, read the first 10 rows of
`runtime/DATA/scan - field test 1 - 19.1/scan_2026-01-19_11-17-03Z-GPS.csv`
to confirm the column names (`gps_lat`, `gps_lon`) and get approximate values.

In the spec, compute the mean at runtime using Node.js `fs` + a quick CSV parse,
or hard-code the mean if it is stable. The file is a standard CSV with a header row.

---

## Task C2 — Write `tests/e2e/validation_19_1.spec.ts`

Model the spec closely on `tests/e2e/demo.spec.ts`. Reuse the same helper functions
(`selectByValueOrText`, `selectExactOption`, `valueForQualityMetric`, `pause`).

The spec must run the **complete** pipeline in this order:

### Step 1 — Session start
Navigate to `/session`, select the `scan - field test 1 - 19.1` folder,
confirm Wi-Fi mode, click Start Session. Assert URL changes to `/overview`.

### Step 2 — Calibration
Navigate to Calibration, select `scan_2026-01-19_11-14-13Z-calic_search1.csv`,
wait for MAC dropdown to populate, select `2c:59:8a:58:95:c1`,
click Run Calibration, wait for parameter table, click Approve.
Assert success banner contains "approved".

### Step 3 — Enrichment
Navigate to Enrichment & Re-ID, select `scan_2026-01-19_11-20-58Z-test-circle2.csv`,
assert PCAP found status, click Run Enrichment.
Wait up to 90s for the enrichment quality panel.
Capture match rate text.

### Step 4 — Re-ID
Select the just-created ENRICHED artifact from the Re-ID dropdown
(filename: `scan_2026-01-19_11-20-58Z-test-circle2_ENRICHED.csv`).
Click Run Re-ID. Wait up to 90s for Re-ID quality panel.
Capture `Static clusters`, `Dynamic clusters`, and `Unique dynamic MACs` metric values.

### Step 5 — Localization
Navigate to Localization, select `scan_2026-01-19_11-20-58Z-test-circle2_REID.csv`.
Click Run Localization. Wait up to 120s for the cluster table.
Capture cluster row count.

**Confidence tiers check:** After the table appears, read the first 5 rows of the
cluster table and collect any confidence badge text (`.conf-badge`). Report what
confidence tiers are visible (or note if the badges are absent — this is a new feature
and may not yet be in the UI if Worker B's changes haven't landed).

Take a screenshot: `tests/e2e/screenshots/validation_step5_localization.png`.

### Step 6 — Result Analysis
Navigate to Result Analysis via the stage nav.
Assert the page heading is visible.

**Add GT point from GPS.csv mean:**
Read `runtime/DATA/scan - field test 1 - 19.1/scan_2026-01-19_11-17-03Z-GPS.csv`
inside the test using `fs.readFileSync`, parse gps_lat and gps_lon from all rows,
compute the mean. Round to 6 decimal places.

Then — look for a file input in the GT import section of the page. Use
`page.setInputFiles` to upload the GPS CSV to any `input[type="file"]` in the
GT panel. If no file input exists, fall back to entering the computed mean
lat/lon manually in the GT form fields and clicking Add.

Wait for a GT point entry to appear in the GT point list (any row in the GT table
or list). Assert at least 1 GT point is present.

Take a screenshot: `tests/e2e/screenshots/validation_step6_gt_added.png`.

### Step 7 — Run Evaluation
Click the "Run Evaluation" (or "Evaluate") button.
Wait up to 30s for results to appear (look for a score value or a matches/FP/FN count).

Capture:
- Total score (look for a numeric value near "Score" or "Total")
- Number of matches
- Number of false positives
- Number of false negatives
- Number of ambiguous GTs (may be 0)

Take a final screenshot: `tests/e2e/screenshots/validation_step7_evaluation.png`.

### Step 8 — Log full report

```typescript
console.log(JSON.stringify({
  folder: FOLDER_ID,
  calibrationMac: CALIBRATION_MAC,
  enrichmentMatchRate,
  reidStaticClusters,
  reidDynamicClusters,
  reidUniqueDynamicMacs,
  localizationClusters,
  confidenceBadgesVisible,    // array of text values found, or [] if none
  gtMeanLat,
  gtMeanLon,
  evaluationScore,
  evaluationMatches,
  evaluationFalsePositives,
  evaluationFalseNegatives,
  evaluationAmbiguous,
}, null, 2))
```

---

## Task C3 — Run the spec

```bash
npx playwright test validation_19_1 --config playwright.demo.config.ts
```

If the test fails at any step, capture the error and the last screenshot, then
continue the report — do not abort silently.

Make sure both the backend (`uvicorn app.main:app --reload`) and frontend
(`npm run dev`) are running before executing the Playwright spec.
If they are not running, start them as background processes.

---

## Acceptance (Worker C)

- [ ] Spec file written at `tests/e2e/validation_19_1.spec.ts`
- [ ] Test runs in headed Chromium (visible to the founder)
- [ ] Full pipeline executed: Calibration → Enrichment → Re-ID → Localization → Result Analysis → Evaluation
- [ ] GT point added from GPS.csv mean coordinates
- [ ] Screenshots captured at steps 5, 6, 7
- [ ] Full JSON report logged to console
- [ ] Any failures or unexpected UI states are described in `.ai/codex_result.md`

---

## Final Step (Supervisor)

After all three workers complete:

```bash
cd backend && python -m pytest tests/unit/ -x -q
cd frontend && npm.cmd run build
```

Report in `.ai/codex_result.md`:
1. Worker A: what changed, test count
2. Worker B: what changed, build output
3. Worker C: full pipeline report (paste the JSON log), screenshots location, any failures
4. Integration issues (if any)
