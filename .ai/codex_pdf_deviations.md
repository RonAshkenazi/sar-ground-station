# Codex PDF Deviation Review - pre-2026-078.pdf

Source reviewed: `docs/pre-2026-078.pdf` (`p-2026-078`, submitted 2025-12-21, 28 pages).
Comparison target: current repo state on 2026-05-12.

## Deviations To Track For Final Report

1. **Airborne unit scope is no longer implemented in the current demo.**
   - PDF describes an Air Unit with Raspberry Pi Zero 2W, Wi-Fi monitor dongle, BLE dongle, GNSS dongle, C2 FastAPI service, heartbeat, scan start/stop, and log offload.
   - Current repo is focused on the Windows local Ground Station demo. Air Unit code is treated as out of scope in `docs/ARCHITECTURE.md`.

2. **C2 / heartbeat / remote file download are not present in the implemented product.**
   - PDF says the operator can start/stop scanning, monitor health over WebSocket, request `GET /logs`, and download logs over Wi-Fi.
   - Current app starts from already-existing local scan folders under `runtime/DATA`; no airborne C2 service or log download flow exists.

3. **BLE is described as part of the system, but implementation is Wi-Fi-first.**
   - PDF repeatedly references Wi-Fi + BLE capture and BLE advertising support, while also noting Wi-Fi is the MVP.
   - Current backend has BLE placeholders only: BLE PCAP parsing is not implemented, enrichment is hardcoded to `protocol="wifi"`, and BLE Re-ID leaves dynamic MACs as singleton clusters.

4. **Performance claims are not yet supportable.**
   - PDF target: Re-ID accuracy >= 90%, uncertainty radius <= 10 m, point error < 10 m, ground truth inside uncertainty circle in >= 90% of tests.
   - Current app has an operational demo, but the real validation suite and field-trial metrics are not yet implemented or measured.

5. **Re-ID algorithm is structurally present but not final.**
   - PDF describes hybrid heuristic + logistic regression inspired by Bleach/Cappuccino, sequence-gap filtering around 64, inter-frame timing, IE similarity, and match probability > 0.9.
   - Current Re-ID uses placeholder constants: association threshold and all Wi-Fi scoring weights are still `1.0`; time window is `1.0 ms`; burst grouping, logistic regression, conflict-resolution post-pass, and robust randomized-MAC association remain sprint-02 work.

6. **Localization algorithm differs from the PDF narrative.**
   - PDF says localization uses WLS plus Bayesian grid updates.
   - Current localization implements a grid/posterior style result, but WLS initialization/refinement is not clearly implemented as described, dynamic sigma is disabled (`0.0`), confidence cutoff is disabled (`0.0`), and LOC-09/10/11 RANSAC pre-cleaning is still stubbed.

7. **Calibration requirements are still incomplete.**
   - PDF assumes calibrated path-loss exponent and stochastic parameters from field experiments.
   - Current calibration exists, but warning thresholds CAL-07/CAL-08 remain TBD, and real environment calibration/validation has not been completed.

8. **Enrichment/PCAP matching is not mature enough for final claims.**
   - PDF depends on extracting stable frame signatures from PCAP/CSV, including IEs and sequence fields.
   - Current enrichment has TODO constants, `_ENR_02_TIME_WINDOW_MS = 500 ms` while sprint-02 expects legacy `1000 ms`, `_ENR_01_MATCH_THRESHOLD = 0.3` while legacy appears closer to `0.8`, and demo PCAP match rate has been observed at `0.0%`.

9. **Vendor/OUI context is missing from new enriched outputs.**
   - PDF and algorithm narrative rely on device/frame signatures and contextual RF metadata.
   - Current enrichment omits `src_vendor` because OUI/vendor DB support is not implemented yet.

10. **Result Analysis and ground-truth workflow are still stubs.**
    - PDF final testing requires comparing MAP location and uncertainty radius to pre-surveyed ground truth across 20 runs.
    - Current `ResultAnalysisPage` is a placeholder and backend result-analysis endpoints return `not_implemented`, so final metric reporting is not available inside the app.

11. **Final test protocol has not been implemented.**
    - PDF defines 20 final runs: 3 integrity, 7 Re-ID, 10 localization/calibration.
    - Current repo has automated backend/frontend/demo tests, but not the PDF's field-test protocol, ground-truth dataset structure, or acceptance-report generator.

12. **Current milestone has expanded past the earlier architecture milestone.**
    - `docs/ARCHITECTURE.md` still says first milestone is operational Wi-Fi workflow through Enrichment.
    - Current app now includes Re-ID, Localization, Save/Resume, and demo flow through localization. The final report should update milestone language to match reality.

13. **Save/Resume exists now, but it is app-specific and not in the PDF architecture.**
    - PDF focuses on Store & Forward from Air Unit to Ground Station.
    - Current implementation adds Ground Station session persistence under `runtime/Saved Scans`, saving session metadata, calibration, localization, and REID artifact after localization.

14. **Storage architecture changed from PDF's local database wording.**
    - PDF says the Ground Station manages a local database for storage.
    - Current Phase 0-4 architecture intentionally uses local filesystem storage and no database.

15. **User flow differs from the PDF.**
    - PDF flow: drone scan -> local Air Unit storage -> offload -> offline analysis.
    - Current demo flow: select existing local scan folder -> Overview -> Calibration -> Enrichment -> Re-ID -> Localization -> Save/Resume.

16. **Map/UI capabilities are narrower than the final report language may imply.**
    - PDF promises probabilistic heatmap visualization and device tracking results.
    - Current localization map displays heatmap/peaks/cluster table, but Result Analysis, rerun controls, ground-truth overlays, and final evaluation views are not implemented.

17. **Search-path optimization from Krypto is literature context only.**
    - PDF discusses Krypto search paths and multi-quadrant sensing geometry.
    - Current app does not plan or optimize drone flight paths; it only analyzes already-collected logs.

18. **Privacy/decryption boundary should be kept explicit.**
    - PDF says only unencrypted management frames are analyzed, with no payload decryption or DPI.
    - Current implementation should preserve this statement, but final report should avoid implying payload analysis or real-time person identification.

19. **Artifact naming and pipeline details changed.**
    - Current canonical artifacts use uppercase suffixes: `*_ENRICHED.csv` and `*_REID.csv`.
    - Final report should use current artifact names and avoid legacy/lowercase naming unless describing historical inputs.

20. **Researcher verification is still pending before algorithm claims are final.**
    - Current `.ai/handoffs/current.md` asks a Researcher to extract authoritative constants from the legacy app and papers.
    - Until that is done, final report should frame the current algorithms as operational scaffolding plus pending algorithm-quality alignment, not fully validated Bleach/Krypto implementations.

