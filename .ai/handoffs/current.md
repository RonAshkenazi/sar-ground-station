# Codex Handoff — Enrichment Rerun from Result Analysis

## Requested Role

[DEV:backend] + [DEV:frontend]

---

## Context

The Result Analysis page already supports two rerun stages from the right-hand panel:
- `"localization"` — re-runs localization only
- `"reid"` — re-runs Re-ID → Localization

This handoff adds a third stage: `"enrichment"` — re-runs **Enrichment → Re-ID → Localization** as a chained 3-stage task. All five enrichment scoring parameters must be exposed in the UI (including the TBD-weight ones). Re-evaluation after rerun stays manual (no auto-trigger).

---

## Files to Change

1. `backend/app/api/result_analysis.py`
2. `frontend/src/pages/ResultAnalysisPage.tsx`
3. `frontend/src/api/sessions.ts`

Do NOT modify engine files, session_store, gt_store, or any other file.

---

## Backend — `backend/app/api/result_analysis.py`

### Step 1 — Update the imports at the top of `rerun_from_result_analysis`

The function currently starts with these inline imports:

```python
from app.api.executions import create_execution
from app.api.localization import (
    _LOC_06_GRID_RESOLUTION_M,
    _LOC_UNCERTAINTY_ALPHA,
    _LOC_UNCERTAINTY_PARTICIPATION_FLOOR,
    _run_localization_task,
)
from app.modules.reid.engine import (
    _REID_01_ASSOCIATION_THRESHOLD,
    _REID_WIFI_BURST_WINDOW_SEC,
    _REID_WIFI_SEQ_GAP_MAX,
    _REID_WIFI_TIME_GAP_MAX_SEC,
)
```

**Replace** those imports with the expanded set:

```python
from app.api.enrichment import _find_matching_pcap
from app.api.executions import create_execution
from app.api.localization import (
    _LOC_06_GRID_RESOLUTION_M,
    _LOC_UNCERTAINTY_ALPHA,
    _LOC_UNCERTAINTY_PARTICIPATION_FLOOR,
    _run_localization_task,
)
from app.modules.enrichment.engine import (
    _ENR_01_MATCH_THRESHOLD,
    _ENR_02_TIME_WINDOW_MS,
    _ENR_03_TIME_SCORE_WEIGHT,
    _ENR_04_IDENTITY_SCORE_WEIGHT,
    _ENR_05_WIFI_CONTEXT_WEIGHT,
)
from app.modules.reid.engine import (
    _REID_01_ASSOCIATION_THRESHOLD,
    _REID_WIFI_BURST_WINDOW_SEC,
    _REID_WIFI_SEQ_GAP_MAX,
    _REID_WIFI_TIME_GAP_MAX_SEC,
)
```

### Step 2 — Add `enrichment_params` extraction

The current extraction block is:

```python
stage = body.get("stage", "localization")
reid_params = body.get("reid_params") or {}
loc_params = body.get("localization_params") or {}
```

**Replace** with:

```python
stage = body.get("stage", "localization")
reid_params = body.get("reid_params") or {}
loc_params = body.get("localization_params") or {}
enrichment_params = body.get("enrichment_params") or {}
```

### Step 3 — Update the stage validation guard

Current:

```python
if stage not in {"localization", "reid"}:
    raise HTTPException(status_code=422, detail="Only localization or reid rerun is supported")
```

**Replace** with:

```python
if stage not in {"localization", "reid", "enrichment"}:
    raise HTTPException(status_code=422, detail="Only localization, reid, or enrichment rerun is supported")
```

### Step 4 — Insert the `enrichment` branch

Insert this entire block **before** `if stage == "reid":`:

```python
if stage == "enrichment":
    enriched_artifact = session.get("active_enriched_artifact")
    if not enriched_artifact:
        raise HTTPException(status_code=422, detail="No active ENRICHED artifact available for Enrichment rerun")
    enriched_path = Path(enriched_artifact)
    original_stem = enriched_path.stem
    if original_stem.upper().endswith("_ENRICHED"):
        original_stem = original_stem[:-9]
    original_csv_path = enriched_path.parent / f"{original_stem}.csv"
    if not original_csv_path.exists():
        raise HTTPException(status_code=422, detail=f"Original scan CSV not found: {original_csv_path.name}")
    pcap_path = _find_matching_pcap(original_csv_path)
    if pcap_path is None:
        raise HTTPException(status_code=422, detail=f"No matching PCAP found for {original_csv_path.name}")
    calibration = session.get("calibration") or session.get("active_calibration")
    if not calibration or calibration.get("approved") is not True:
        raise HTTPException(status_code=422, detail="No calibration available for Enrichment rerun")
    execution_id = create_execution("enrichment_reid_localization")
    background_tasks.add_task(
        _run_enrichment_then_reid_then_localization_task,
        execution_id,
        session_id,
        original_csv_path,
        pcap_path,
        session.get("mode", "wifi"),
        calibration["parameters"],
        {
            "match_threshold": enrichment_params.get("match_threshold", _ENR_01_MATCH_THRESHOLD),
            "time_window_ms": enrichment_params.get("time_window_ms", _ENR_02_TIME_WINDOW_MS),
            "time_score_weight": enrichment_params.get("time_score_weight", _ENR_03_TIME_SCORE_WEIGHT),
            "identity_score_weight": enrichment_params.get("identity_score_weight", _ENR_04_IDENTITY_SCORE_WEIGHT),
            "context_weight": enrichment_params.get("context_weight", _ENR_05_WIFI_CONTEXT_WEIGHT),
        },
        {
            "association_threshold": reid_params.get("association_threshold", _REID_01_ASSOCIATION_THRESHOLD),
            "seq_gap_max": reid_params.get("seq_gap_max", _REID_WIFI_SEQ_GAP_MAX),
            "time_gap_max_sec": reid_params.get("time_gap_max_sec", _REID_WIFI_TIME_GAP_MAX_SEC),
            "burst_window_sec": reid_params.get("burst_window_sec", _REID_WIFI_BURST_WINDOW_SEC),
            "probe_requests_only": reid_params.get("probe_requests_only", False),
        },
        loc_params,
    )
    session["last_evaluation"] = None
    return {"status": "pending", "execution_id": execution_id}
```

### Step 5 — Add the new background task function

Append this function after `_run_reid_then_localization_task` (at the bottom of the file):

```python
def _run_enrichment_then_reid_then_localization_task(
    execution_id: str,
    session_id: str,
    csv_path: Path,
    pcap_path: Path,
    protocol: str,
    calibration_parameters: dict,
    enrichment_params: dict,
    reid_params: dict,
    loc_params: dict,
) -> None:
    from app.api.executions import update_execution
    from app.modules.enrichment.engine import run_enrichment
    from app.modules.localization.engine import (
        _LOC_02_SEARCH_AREA_BUFFER_M,
        _LOC_06_GRID_RESOLUTION_M,
        _LOC_07_DYNAMIC_SIGMA_ALPHA,
        _LOC_08_CONFIDENCE_CUTOFF,
        _LOC_UNCERTAINTY_ALPHA,
        _LOC_UNCERTAINTY_PARTICIPATION_FLOOR,
        run_localization,
    )
    from app.modules.reid.engine import run_reid
    from app.modules.session_navigation.session_store import get_session

    update_execution(execution_id, status="running")
    try:
        enr_result = run_enrichment(
            csv_path=csv_path,
            pcap_path=pcap_path,
            protocol=protocol,
            **enrichment_params,
        )
        enriched_csv_path = Path(enr_result["enriched_csv_path"])
        reid_result = run_reid(
            enriched_csv_path=enriched_csv_path,
            protocol=protocol,
            **reid_params,
        )
        reid_csv_path = Path(reid_result["reid_csv_path"])
        loc_result = run_localization(
            reid_csv_path=reid_csv_path,
            calibration=calibration_parameters,
            bounds_mode=loc_params.get("bounds_mode", "auto_track_plus_buffer"),
            buffer_m=loc_params.get("buffer_m", _LOC_02_SEARCH_AREA_BUFFER_M),
            manual_bounds=None,
            grid_resolution_m=loc_params.get("grid_resolution_m", _LOC_06_GRID_RESOLUTION_M),
            dynamic_sigma_alpha=loc_params.get("dynamic_sigma_alpha", _LOC_07_DYNAMIC_SIGMA_ALPHA),
            confidence_cutoff=loc_params.get("confidence_cutoff", _LOC_08_CONFIDENCE_CUTOFF),
            uncertainty_participation_floor=loc_params.get(
                "uncertainty_participation_floor",
                _LOC_UNCERTAINTY_PARTICIPATION_FLOOR,
            ),
            uncertainty_alpha=loc_params.get("uncertainty_alpha", _LOC_UNCERTAINTY_ALPHA),
        )
        session = get_session(session_id)
        if session is not None:
            session["active_enrichment"] = {
                "enriched_csv_path": enr_result["enriched_csv_path"],
                "quality": enr_result,
            }
            session["active_enriched_artifact"] = enr_result["enriched_csv_path"]
            session["active_reid"] = {
                "reid_csv_path": reid_result["reid_csv_path"],
                "quality": reid_result,
            }
            session["active_reid_artifact"] = reid_result["reid_csv_path"]
            session["active_localization"] = loc_result
            session["current_localization_result"] = loc_result
        update_execution(
            execution_id,
            status="success",
            warnings=[
                *enr_result.get("warnings", []),
                *reid_result.get("warnings", []),
                *loc_result.get("warnings", []),
            ],
            result_metadata={
                "enrichment": enr_result,
                "reid": reid_result,
                "localization": loc_result,
            },
            error=None,
        )
    except Exception as exc:  # pragma: no cover
        update_execution(execution_id, status="failed", error=str(exc))
```

---

## Frontend API — `frontend/src/api/sessions.ts`

### Update `rerunFromResultAnalysis`

Find the current signature:

```typescript
export const rerunFromResultAnalysis = (
  session_id: string,
  stage: 'localization' | 'reid',
  localization_params?: {
    grid_resolution_m?: number
    dynamic_sigma_alpha?: number
    confidence_cutoff?: number
    uncertainty_participation_floor?: number
    uncertainty_alpha?: number
    buffer_m?: number
  },
  reid_params?: {
    association_threshold?: number
    seq_gap_max?: number
    time_gap_max_sec?: number
    burst_window_sec?: number
    probe_requests_only?: boolean
  },
) =>
  apiFetch<{ status: string; execution_id?: string; localization_execution_id?: string }>(
    `/api/sessions/${session_id}/result-analysis/rerun`,
    {
      method: 'POST',
      body: JSON.stringify({ stage, localization_params, reid_params }),
    },
  )
```

**Replace** with:

```typescript
export const rerunFromResultAnalysis = (
  session_id: string,
  stage: 'localization' | 'reid' | 'enrichment',
  localization_params?: {
    grid_resolution_m?: number
    dynamic_sigma_alpha?: number
    confidence_cutoff?: number
    uncertainty_participation_floor?: number
    uncertainty_alpha?: number
    buffer_m?: number
  },
  reid_params?: {
    association_threshold?: number
    seq_gap_max?: number
    time_gap_max_sec?: number
    burst_window_sec?: number
    probe_requests_only?: boolean
  },
  enrichment_params?: {
    match_threshold?: number
    time_window_ms?: number
    time_score_weight?: number
    identity_score_weight?: number
    context_weight?: number
  },
) =>
  apiFetch<{ status: string; execution_id?: string; localization_execution_id?: string }>(
    `/api/sessions/${session_id}/result-analysis/rerun`,
    {
      method: 'POST',
      body: JSON.stringify({ stage, localization_params, reid_params, enrichment_params }),
    },
  )
```

---

## Frontend Page — `frontend/src/pages/ResultAnalysisPage.tsx`

### Change 1 — Update `rerunStage` type and add `enrichmentParams` state

Find:

```typescript
const [rerunStage, setRerunStage] = useState<'localization' | 'reid'>('localization')
```

**Replace** with:

```typescript
const [rerunStage, setRerunStage] = useState<'localization' | 'reid' | 'enrichment'>('localization')
const [enrichmentParams, setEnrichmentParams] = useState({
  match_threshold: 0.3,
  time_window_ms: 1000.0,
  time_score_weight: 1.0,
  identity_score_weight: 1.0,
  context_weight: 0.5,
})
```

### Change 2 — Update `handleRerun` to pass enrichment params

Find the `rerunFromResultAnalysis` call inside `handleRerun`:

```typescript
const started = await rerunFromResultAnalysis(
  session.session_id,
  rerunStage,
  localizationParams,
  rerunStage === 'reid' ? reidParams : undefined,
)
```

**Replace** with:

```typescript
const started = await rerunFromResultAnalysis(
  session.session_id,
  rerunStage,
  localizationParams,
  rerunStage === 'reid' || rerunStage === 'enrichment' ? reidParams : undefined,
  rerunStage === 'enrichment' ? enrichmentParams : undefined,
)
```

### Change 3 — Add third radio button in the stage selector

Find the two existing radio buttons in the rerun section:

```tsx
<label>
  <input
    type="radio"
    checked={rerunStage === 'localization'}
    onChange={() => setRerunStage('localization')}
  />
  Localization only
</label>
<label>
  <input type="radio" checked={rerunStage === 'reid'} onChange={() => setRerunStage('reid')} />
  Re-ID + Loc
</label>
```

**Replace** with:

```tsx
<label>
  <input
    type="radio"
    checked={rerunStage === 'localization'}
    onChange={() => setRerunStage('localization')}
  />
  Localization only
</label>
<label>
  <input type="radio" checked={rerunStage === 'reid'} onChange={() => setRerunStage('reid')} />
  Re-ID + Loc
</label>
<label>
  <input
    type="radio"
    checked={rerunStage === 'enrichment'}
    onChange={() => setRerunStage('enrichment')}
  />
  Enrichment + Re-ID + Loc
</label>
```

### Change 4 — Add enrichment params section and update re-ID params visibility

Find the existing Re-ID params section:

```tsx
{rerunStage === 'reid' && (
  <>
    <h3 className="param-heading">Re-ID params</h3>
```

**Replace** the entire condition opening with:

```tsx
{rerunStage === 'enrichment' && (
  <>
    <h3 className="param-heading">Enrichment params</h3>
    {Object.entries(enrichmentParams).map(([k, v]) => (
      <label key={k} className="param-row">
        <span className="mono">{k}</span>
        <input
          type="number"
          step="any"
          value={v}
          onChange={e =>
            setEnrichmentParams(p => ({ ...p, [k]: parseFloat(e.target.value) }))
          }
        />
      </label>
    ))}
  </>
)}
{(rerunStage === 'reid' || rerunStage === 'enrichment') && (
  <>
    <h3 className="param-heading">Re-ID params</h3>
```

The closing `</>` and `)}` of the old `rerunStage === 'reid'` block stays — just the opening condition has changed to `(rerunStage === 'reid' || rerunStage === 'enrichment')`.

---

## Verification

1. Start backend: `cd backend && uvicorn app.main:app --reload`
2. Load a scan folder that has an ENRICHED artifact and calibration approved
3. Navigate to Result Analysis
4. In the Rerun panel, select "Enrichment + Re-ID + Loc"
5. Confirm enrichment params appear (match_threshold, time_window_ms, etc.) AND re-ID params appear below
6. Click Rerun — it should poll to success
7. The map should refresh with updated clusters
8. Score panel stays blank (no auto re-evaluate — must click Run Evaluation manually)
9. Change `match_threshold` to a very low value (e.g. 0.05) and rerun again — verify the match_rate changes in the execution result_metadata

---

## Acceptance Criteria

- [ ] `"enrichment"` accepted by backend rerun endpoint without 422
- [ ] Backend derives original CSV path by stripping `_ENRICHED` suffix
- [ ] Backend finds PCAP via `_find_matching_pcap`
- [ ] 3-stage task runs: enrichment → reid → localization in sequence
- [ ] Session updated: `active_enriched_artifact`, `active_reid_artifact`, `active_localization`, `current_localization_result`
- [ ] `session["last_evaluation"]` set to None at rerun start
- [ ] Frontend radio button "Enrichment + Re-ID + Loc" appears in Rerun panel
- [ ] All 5 enrichment params shown and editable when stage is enrichment
- [ ] Re-ID params section also shown when stage is enrichment
- [ ] Existing "localization only" and "Re-ID + Loc" stages unaffected

---

## Constraints

- Only modify the three listed files
- Do NOT change engine files (`enrichment/engine.py`, `reid/engine.py`, `localization/engine.py`)
- Do NOT change `session_store.py`, `gt_store.py`, or canonical models
- Do NOT run `git commit`
- All file I/O in the task function must follow the existing pattern from `_run_reid_then_localization_task`
- If original CSV or PCAP not found: HTTP 422 with clear message (no silent fallback)
