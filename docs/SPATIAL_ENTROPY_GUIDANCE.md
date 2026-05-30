# Spatial Entropy Guidance Design

Date: 2026-05-15

## Summary

Spatial entropy guidance adds two phase-1 behaviors to the live mission guidance engine:

- RF evidence propagates from the packet cell into its 8-connected neighbors.
- The backend reports evidence freshness, spatial entropy, certainty, and display score per cell.

The goal is to make the grid reflect physical RF spread without making empty or stale cells look like hard targets.

## Current Baseline

Existing cell scores:

```text
E_i = evidence score
V_i = coverage score
A_i = age score
U_i = 0.6 * (1 - V_i) + 0.4 * A_i
P_i = peakness
D_i = travel cost
R_i = oscillation penalty
J_i = final guidance score
```

Before this design, `POSE` and `EVIDENCE` only updated the exact cell containing the packet lat/lon.

## Evidence Propagation

For an evidence packet mapped to source cell `x`:

```text
raw_e = compute_evidence_raw(rssi_p95, rssi_max, frames_total, frames_strong)
```

Apply a 3x3 kernel:

```text
K(x, x) = 1.00
K(x, orthogonal neighbor) = 0.25
K(x, diagonal neighbor) = 0.15
```

Each affected neighbor receives:

```text
E_j <- EMA(E_j, K(x, j) * raw_e)
```

Default config:

```text
NEIGHBOR_EVIDENCE_ALPHA_ORTH = 0.25
NEIGHBOR_EVIDENCE_ALPHA_DIAG = 0.15
```

## Dwell Propagation

POSE dwell updates the source cell strongly and neighbors weakly.

```text
V_x <- update_coverage(V_x, dwell_ms)
V_neighbor <- update_coverage(V_neighbor, 0.20 * K_cov * dwell_ms)
```

Defaults:

```text
NEIGHBOR_COVERAGE_BETA = 0.20
NEIGHBOR_COVERAGE_ALPHA_ORTH = 1.00
NEIGHBOR_COVERAGE_ALPHA_DIAG = 0.70
```

## Spatial Entropy

For each cell `i`, compute local entropy over `N9(i) = i + 8-connected neighbors`.

Fresh evidence mass:

```text
M_j(t) = E_j * exp(-(t - last_seen_j_ms) / TAU_EVIDENCE_DECAY_MS)
TAU_EVIDENCE_DECAY_MS = 300_000
```

Normalize:

```text
p_j = (M_j + epsilon) / sum(M_k + epsilon for k in N9(i))
epsilon = 1e-6
```

Entropy:

```text
H_i = -sum(p_j * ln(p_j)) / ln(len(N9(i)))
C_i = 1 - H_i
```

Interpretation:

- `H_i ~= 0`: localized RF peak.
- `H_i ~= 1`: diffuse/ambiguous RF field.
- `C_i`: spatial certainty.

If local mass is below `ENTROPY_MIN_MASS = 0.05`, return:

```text
H_i = 1.0
C_i = 0.0
```

## API Fields

Each grid cell should expose:

```text
spatial_entropy
spatial_certainty
evidence_freshness
display_score
```

Compatibility aliases may remain:

```text
entropy_score
evidence_freshness_score
```

## UI Semantics

The emulator and future map display should color cells by:

```text
display_score ?? evidence_score
```

Palette:

- `0.00`: dark gray, no evidence.
- `0.01-0.10`: red, weak/echo evidence.
- `0.10-0.30`: orange, plausible RF.
- `0.30-0.60`: yellow, strong RF.
- `>=0.60`: green, high-confidence RF.

Tooltips should show separate values:

```text
E, fresh, U, H, C, J
```

## Target Selection

Propagation creates weak echo evidence, so target selection must not treat any `E_i > 0` as a full target candidate.

Phase-1 rule:

```text
candidate if E_i >= E_TARGET_MIN and E_i >= 0.5 * max_evidence
E_TARGET_MIN = 0.05
```

If no evidence candidate exists, keep the current fallback:

```text
target = current valid Pi GPS cell
```

## Emulator Scenarios

The browser emulator should validate:

- Single strong stationary source.
- Two adjacent source-like detections.
- Broad weak noise.
- Stale evidence / no packets.
- Drone dwell without evidence.

Packet cadence:

- POSE: selectable, default `1 Hz`.
- EVIDENCE: selectable, default every `3s`.

## Phase Boundary

Phase 1 implements propagation, entropy fields, display score, and emulator.

Phase 2 may add entropy directly to final target scoring after live validation.
