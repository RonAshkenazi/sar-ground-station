# Product Requirements Document

## 1. Overview

**Project Name:** SAR Ground Station

**One-line description:** A ground station application for loading drone-collected RF scan data, enriching it, re-identifying devices, localizing emitters, analyzing results, and saving resumable sessions.

**Problem:** SAR teams and the research team need a reliable way to inspect Wi-Fi/BLE RF scans, process them through a repeatable pipeline, and evaluate possible device locations. The legacy app works, but its behavior is not cleanly modular, not easy enough to extend, and not rigorous enough around artifacts, state ownership, reruns, and save/resume.

**Target Users:**

- Operational SAR users who need to run the scan-processing workflow and inspect localization results.
- Research/tuning users who need to evaluate output quality, compare against ground truth, adjust parameters, and rerun controlled stages.

**Source of Truth:** Detailed behavior is governed by `docs/Part A.md` and `docs/Part B.md`. Implementation order is governed by `docs/Part C.md`.

## 2. MVP Scope

The MVP is the Ground Station refactor only. The Air Unit / Airborne side is reference-only and out of scope.

The first development target is Phase 0 through Phase 4 from `docs/Part C.md`, ending after a working Wi-Fi enrichment flow.

## 3. Core Features

| # | Feature | Description | Priority |
|---|---------|-------------|----------|
| 1 | Session start and scan folder discovery | List scan folders from `DATA/`, detect Wi-Fi/BLE mode, allow manual mode override, create active session state. | Must Have |
| 2 | Inventory and artifact activation | List CSV, PCAP, `*_ENRICHED.csv`, and `*_REID.csv` files; activate official artifacts immediately and suggest next stage. | Must Have |
| 3 | Overview inspection | Select a CSV, show basic statistics, charts, preview table, spatial inspection, and device analysis without advanced processing. | Must Have |
| 4 | Calibration | Derive or select session-level calibration parameters from selected CSV/MAC and store approved calibration. | Must Have |
| 5 | Enrichment and Re-ID | Generate official ENRICHED artifacts from CSV+PCAP and generate REID artifacts with `cluster_id` and `cluster_type`. | Must Have |
| 6 | Localization and layered map | Run localization on full or filtered REID data and present per-cluster results through a layered spatial view. | Must Have |
| 7 | Legacy algorithm research | Compare legacy algorithm behavior against Parts A/B/C, identify assumptions, and recommend which behavior to preserve, change, or mark TBD. | Must Have |
| 8 | Save and resume | Save complete sessions into `Saved Scans` and resume without relying on `TEMP`. | Should Have |

## 4. User Stories

### Story 1: Start a Scan Session

As an operational SAR user, I want to select a scan folder from `DATA/`, so that I can begin working on a specific RF scan session.

**Acceptance Criteria:**

- [ ] System lists subfolders from `DATA/`.
- [ ] System detects mode from folder name as Wi-Fi, BLE, or unknown.
- [ ] User can manually override mode.
- [ ] Creating a session stores active folder and mode.
- [ ] After session creation, the app opens Overview.
- [ ] If no valid CSV exists, Overview still opens with a warning.

### Story 2: Inspect Raw Scan Data

As an operational SAR user, I want to inspect a selected CSV before advanced processing, so that I can verify that the scan data looks usable.

**Acceptance Criteria:**

- [ ] Overview shows no file-level outputs until a CSV is selected.
- [ ] User can select a CSV from the active folder.
- [ ] System shows summary statistics, charts, preview table, spatial inspection, and device analysis.
- [ ] Partial or incomplete data is displayed with warnings instead of crashing.
- [ ] Overview does not perform enrichment, Re-ID, or localization.

### Story 3: Prepare Calibration

As an operational SAR user, I want to derive or choose calibration parameters, so that localization can use approved session-level parameters.

**Acceptance Criteria:**

- [ ] User selects calibration CSV.
- [ ] User selects one MAC address from that CSV.
- [ ] Calibration derivation only uses rows for the selected MAC.
- [ ] System displays derived parameters and fit diagnostics.
- [ ] User can approve derived parameters.
- [ ] If derivation fails or is skipped, fallback theoretical parameter sets remain available.

### Story 4: Enrich and Re-Identify Devices

As an operational SAR user, I want to enrich scan data with PCAP metadata and run Re-ID, so that dynamic identities can be clustered before localization.

**Acceptance Criteria:**

- [ ] Enrichment requires a PCAP with the same basename as the selected CSV.
- [ ] Enrichment writes an official `*_ENRICHED.csv` artifact and silently overwrites an existing one.
- [ ] Enriched rows preserve original scan fields and include match diagnostics.
- [ ] Re-ID consumes an active enriched artifact.
- [ ] REID output writes an official `*_REID.csv` artifact and silently overwrites an existing one.
- [ ] Every relevant REID row includes `cluster_id` and `cluster_type`.

### Story 5: Localize and Inspect Results

As an operational SAR user, I want to run localization and inspect map layers, so that I can identify likely emitter locations.

**Acceptance Criteria:**

- [ ] Localization requires an active REID artifact.
- [ ] User can run localization on the full REID file or filtered subset.
- [ ] Failed clusters produce warnings while successful clusters continue.
- [ ] Each successful cluster exposes a primary peak, candidate peaks, uncertainty regions, and heatmap/grid metadata.
- [ ] Map view controls do not trigger reruns.
- [ ] Rendering logic does not compute localization results.

### Story 6: Analyze and Rerun

As a research user, I want to compare localization results against ground truth and rerun controlled stages, so that I can tune parameters and evaluate quality.

**Acceptance Criteria:**

- [ ] Ground truth exists only in Result Analysis.
- [ ] Ground truth is represented as points, one point per real emitter.
- [ ] Result Analysis computes quality metrics and numeric score once scoring details are approved.
- [ ] Parameter/filter changes rerun only required downstream stages.
- [ ] View-only changes trigger no rerun.

### Story 7: Verify Legacy Algorithms

As a research user, I want the legacy algorithms reviewed against the new specification, so that we do not blindly preserve uncertain or incorrect behavior.

**Acceptance Criteria:**

- [ ] Researcher role can inspect the legacy app as reference-only context.
- [ ] Legacy behavior is mapped to Parts A, B, and C.
- [ ] Hidden assumptions and unexplained numeric defaults are identified.
- [ ] Spec-compliant behavior is separated from legacy behavior that needs founder approval.
- [ ] Legacy outputs can be compared against new outputs for the Wi-Fi enrichment milestone.
- [ ] No Air Unit / Airborne behavior is modified as part of this work.

### Story 8: Save and Resume

As a user, I want to save and resume a session, so that analysis can continue later without relying on temporary files.

**Acceptance Criteria:**

- [ ] Save Session writes persistent session data under `Saved Scans`.
- [ ] Save Session copies or exports required artifacts.
- [ ] Resume restores current result, parameters, ground truth, and view state when present.
- [ ] Resume works even if `TEMP` was cleared.

## 5. Out Of Scope

- Air Unit / Airborne side changes.
- Future live connectivity page for real-time packets.
- Unapproved algorithm defaults for fields marked `TBD`.
- Product features not described in `docs/Part A.md` or `docs/Part B.md`.
- Internal variant history beyond separate saved sessions.

## 6. Success Criteria

- [ ] Backend and frontend run locally.
- [ ] Session can be created from a scan folder.
- [ ] Inventory lists raw and official artifacts correctly.
- [ ] Official ENRICHED and REID artifacts can be activated immediately.
- [ ] First milestone demonstrates Wi-Fi scan folder selection through enrichment artifact generation.
- [ ] Legacy Wi-Fi enrichment behavior has been reviewed by the Researcher role before replacement.
- [ ] Pipeline stages follow strict module boundaries.
- [ ] Save/resume does not depend on `TEMP`.
- [ ] Unit, integration, API contract, and E2E tests cover the implemented scope.
- [ ] Legacy-critical behavior is validated through fixtures or side-by-side checks before replacement.

## 7. Technical Constraints

- **Must use:** Python FastAPI backend and TypeScript/React frontend unless the founder changes this decision.
- **Must support first:** Windows-only development and demo environment.
- **Must demo first:** Operational SAR workflow with Wi-Fi data.
- **Must use:** Canonical data models for cross-module contracts.
- **Must preserve:** Official artifact suffix rules for `*_ENRICHED.csv` and `*_REID.csv`.
- **Must not use:** Hidden page-level session state for shared workflow state.
- **Must not use:** Direct cross-module imports outside approved public interfaces.
- **Must not do:** Invent `TBD` defaults.

## 8. Founder Questions

Answered:

1. Demo target: operational SAR workflow only.
2. First demo dataset: Wi-Fi.
3. Legacy goal: do not blindly preserve algorithms. The refactor exists partly because algorithm behavior is uncertain. Add a Researcher role to verify legacy algorithms against Parts A/B/C.
4. Runtime storage during development: use repo-local ignored folders under `runtime/`.
5. First supported OS: Windows only.
6. Frontend target: browser app for now.
7. Legacy app and datasets can be copied into the agreed local reference/runtime folders, but they must remain ignored by git.
8. First milestone: working flow through Enrichment.

Open:

- Which exact Wi-Fi scan folder should be the first demo fixture?
- Which legacy app command or UI flow produces the current trusted enrichment output?
- Are there known legacy enrichment bugs we should intentionally avoid preserving?

## 9. Local Folder Convention

Use these local folders during development:

```text
runtime/
  DATA/          # copied scan folders and raw/official artifacts
  TEMP/          # non-persistent working files
  Saved Scans/   # persistent save/resume packages
reference/
  legacy_app/    # read-only copy of the working legacy app
```

These folders are for local development context and data. Their contents should not be committed.
