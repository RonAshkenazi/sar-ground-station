# Codex Result - Result Analysis Ratio Gate + Multi-GT QA

Date: 2026-05-29

## Part A - Researcher: Ratio Gate Analysis

### Ratio gate mechanics (brief explanation of current logic)

`backend/app/modules/result_analysis/engine.py` builds a prediction-to-GT distance matrix, then populates a cost matrix only for GTs that pass the gate. For each GT, the engine sorts clusters by distance, calls the nearest distance `d1`, the second-nearest distance `d2`, and computes `ratio = d2 / d1`. The nearest cluster becomes eligible for assignment only when `ratio >= ratio_gate`; otherwise the GT is added to `pack_ambiguous_gt_indices` and excluded from matching.

Key code paths:

- `engine.py:51-69`: per-GT nearest/second-nearest ratio gate.
- `engine.py:71`: `_linear_sum_assignment(cost)` assigns only finite cost cells.
- `engine.py:260-270`: SciPy linear assignment is used when available, otherwise `_greedy_assignment`.
- `engine.py:273-286`: greedy fallback sorts finite costs and selects non-conflicting pairs.
- `engine.py:187-195`: score components depend on resulting `matches`; if all GTs are ambiguous, containment, distance, recall, precision, and total score can all collapse to zero.

`frontend/src/pages/ResultAnalysisPage.tsx` already exposes the parameter:

- Default `ratio_gate: 2.0` at line 42.
- Editable numeric input at lines 331-332.

### Observed failure mode (why score = 0)

The gate is applied before assignment. If no GT passes the ratio gate, the cost matrix remains all `_GATE_INF`, `_linear_sum_assignment()` returns no pairs, and `matches = []`. Ambiguous GTs are not counted as false negatives and are not scored as matches. With no matches:

- `coverage = 0.0`
- `median_error_m = None`, so distance score becomes `0.0`
- large prediction/GT count mismatch can make count score `0.0`
- large median radius can make radius score `0.0`

In a reproduced saved-session case with 3 GT points and 102 localization predictions, all three GTs failed the current default gate:

| GT | nearest d1 | second d2 | d2/d1 |
| --- | ---: | ---: | ---: |
| 1 | 69.70m | 77.19m | 1.107 |
| 2 | 40.57m | 51.02m | 1.258 |
| 3 | 91.42m | 95.86m | 1.049 |

Evaluation results on the same session:

| ratio_gate | matches | ambiguous_gts | n_gt | n_predictions | score |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 1.0 | 3 | 0 | 3 | 102 | 0.4 |
| 1.1 | 2 | 1 | 3 | 102 | 0.4 |
| 1.2 | 1 | 2 | 3 | 102 | 0.4 |
| 1.5 | 0 | 3 | 3 | 102 | 0.0 |
| 2.0 | 0 | 3 | 3 | 102 | 0.0 |

This confirms the founder's "score = 0" report for dense or over-split prediction sets. The actual reproduced result is denser than the handoff's 5-15 cluster assumption, but it is the same mechanism: tightly packed competing clusters keep `d2/d1` close to 1.

For the requested 5-15 cluster scenario, I ran deterministic distance-ratio simulations in a 200m x 200m area:

- If GTs are close to a true isolated cluster, 2.0 often still passes at least one GT, but it increasingly drops some GTs as cluster count rises.
- If candidate clusters are grid-like/dense around the operating area, the median `d2/d1` is about 1.68 and the chance that all 3 GTs pass gate 2.0 is only about 5-7%.
- In dense cases, at least one GT usually passes 1.2, often passes 1.5, and may fail 2.0 depending on placement. The reproduced real session is stricter: only gate <= 1.258 produced any clear match.

### Tradeoff table (ratio_gate values vs. behavior)

| Value | Behavior | Tradeoff |
| --- | --- | --- |
| `1.2` | Permissive but still rejects near ties. Requires second-nearest to be at least 20% farther than nearest. | Best default among the listed options. It prevents exact/near ties from being treated as certain, while avoiding the current all-ambiguous failure in dense outputs. |
| `1.5` | Moderate. Requires nearest to be meaningfully dominant: second-nearest 50% farther. | Good for clean, sparse cluster sets. Too strict for dense SAR outputs; reproduced session produced 0 matches. |
| `2.0` | Strict. Requires nearest to be at least 2x closer than second-nearest. | Overly strict for this app's current localization/re-ID outputs. Produces all-ambiguous GTs and score 0 when many clusters are close. |
| disabled / nearest-only | Always lets each GT's nearest prediction compete in assignment, subject to max distance. | Useful as a diagnostic or "score everything" mode. It hides ambiguity, so it should not be the only SAR correctness signal. |

### Recommendation

- Recommended default value: `1.2`.
- Justification: `1.2` is the lowest listed threshold that still has a real ambiguity meaning: the nearest cluster must be at least about 17% closer than the second-nearest (`d1 <= 0.833 * d2`). It kept one GT match in the reproduced dense session where `1.5` and `2.0` both produced zero matches, while still flagging two GTs whose nearest and second-nearest clusters were close. This preserves the purpose of ambiguity detection without breaking the evaluation loop by default.
- Should it remain user-tunable? Yes. The UI already exposes it, and this should stay tunable because sparse clean missions and dense/over-split missions need different strictness. Consider adding inline helper text explaining that lower values are more permissive and `1.0` approximates nearest-neighbor assignment.
- Any alternative matching strategy worth considering? Yes: keep ratio gating as a diagnostic flag, but always produce a nearest-neighbor/linear-assignment score. For example, return `matches` with `association_status: "ambiguous_match"` when `ratio < gate` instead of excluding them from scoring entirely, or report two scores: "strict clear-match score" and "nearest-assignment score".

## Part B - QA: Multi-GT Map Visibility + Evaluation

### Issue 1 - Map visibility

- Root cause: other / UX workflow, not confirmed backend or rendering data loss.
- Evidence:
  - Backend `gt_store.py:23` appends with `_gt_store.setdefault(session_id, []).append(point)`.
  - `get_result_analysis()` returns `gt_points: get_gt_points(session_id)` at `backend/app/api/result_analysis.py:48`.
  - Evaluation loads the same full list at `backend/app/api/result_analysis.py:112`.
  - Frontend renders the GT list from `(raState?.gt_points ?? [])` at `ResultAnalysisPage.tsx:310`.
  - Frontend renders map GT markers from `(raState?.gt_points ?? [])` at `ResultAnalysisPage.tsx:553`.
  - Playwright reproduction, repeating "Add from map" before each click: GT rows increased 0 -> 1 -> 2 -> 3, and GT map path count increased 34 -> 35 -> 36 -> 37.
  - API after those 3 clicks returned exactly 3 `gt_points`.
- Is the backend storing all GT points correctly? Yes, for a consistent `session_id`.
- Is the frontend rendering all GT points? Yes in the reproduced workflow; all 3 GT points appeared in the list and map DOM.

Important UX finding: `handleAddGt()` calls `setAddingGt(false)` after each point at `ResultAnalysisPage.tsx:140`. `GtClickHandler` only adds a point while `enabled` is true (`ResultAnalysisPage.tsx:676-681`). Therefore, "Add from map" is one-shot. A separate reproduction clicked "Add from map" once and then clicked the map three times; the UI and API both ended with only 1 GT point. If the founder expected add mode to stay active, this explains the report without a backend storage bug.

### Issue 2 - Evaluation correctness

- n_gt in evaluation response with 3 stored GTs: `3`.
- Are all GTs used in evaluation? Yes. The evaluation response used all 3 GTs: at `ratio_gate = 2.0`, `n_gt = 3`, `matches = 0`, `ambiguous_gts = 3`, and `false_negatives = 0`.
- Any unexpected behavior observed? The evaluation correctly used all 3 GTs, but the default ratio gate classified all 3 as ambiguous in the reproduced dense saved session, causing `score.total = 0.0`. Lowering the gate changed the counts: `1.2` produced 1 match and 2 ambiguous GTs; `1.0` produced 3 matches and 0 ambiguous GTs.

### Suggested fixes (describe only, do not implement)

- Change the default `ratio_gate` from `2.0` to `1.2`, subject to founder approval.
- Keep `ratio_gate` user-tunable.
- Consider changing ambiguous GT handling so ambiguity does not erase the entire score. Options: score nearest assignments but flag ambiguous status, or show both strict and nearest-assignment scores.
- Improve Add-from-map UX. Either keep add mode active until the user toggles it off, or make the one-shot behavior explicit with clearer button state/copy. The current one-shot behavior is easy to misread as a persistent add mode.
- If the founder still sees only one marker while the GT list/API show multiple points, next check for marker overlap at nearly identical coordinates or map layer styling after an evaluation overlay.

## Acceptance Criteria

- [x] Part A: Ratio gate mechanics explained, tradeoff table provided, recommended default with justification.
- [x] Part B Issue 1: Root cause of single-GT-on-map identified as likely one-shot Add-from-map UX; backend and frontend multi-GT storage/rendering both verified.
- [x] Part B Issue 2: Confirmed evaluation runs against all stored GT points.
- [x] No backend or frontend code changed.
