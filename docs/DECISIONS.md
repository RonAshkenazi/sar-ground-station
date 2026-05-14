# Decision Log

> Document important technical decisions here.
> This helps your future self (and teammates) understand WHY things are the way they are.

---

## Template

Copy this for each new decision:

```markdown
## Decision: [Title]

**Date:** YYYY-MM-DD
**Status:** Proposed / Accepted / Deprecated
**Decided by:** [who]

**Context:**
What is the issue? Why does this decision need to be made?

**Options Considered:**
1. Option A — [pros / cons]
2. Option B — [pros / cons]
3. Option C — [pros / cons]

**Decision:**
We chose Option X.

**Rationale:**
Why this option? What tradeoffs are we accepting?

**Consequences:**
What changes because of this decision?
```

---

## Decisions

## Decision: Packet-count fallback for live guidance evidence

**Date:** 2026-05-15
**Status:** Proposed
**Decided by:** CTO / Founder pending

**Context:**
Live Air Unit status logs include packet counters, GPS fix, position, and channel, for example:

```text
[status] Packets: 144595 | GPS Fix: 1 | Pos: 31.25911, 34.79389 | Chan: 1
```

These logs can identify packet activity near the current Pi GPS cell, but they do not include RSSI summaries.

**Options Considered:**
1. Ignore status logs for guidance evidence and rely only on structured `EVIDENCE` packets with RSSI.
2. Use packet counter deltas from status logs as a fallback activity score when structured RSSI evidence is unavailable.
3. Treat status-log packet deltas as equivalent to RSSI evidence.

**Decision:**
Keep this as a future fallback option only. If implemented, packet-count deltas should be modeled as coarse activity evidence, not as authoritative RF strength evidence.

**Rationale:**
The status log has enough data to map packet activity to a grid cell:

```text
cell_id = lat/lon -> grid cell
frames_total = current_packet_count - previous_packet_count
```

It does not provide `rssi_max_dbm`, `rssi_p95_dbm`, or `rssi_mean_dbm`, so it cannot distinguish strong nearby signals from weak distant/background traffic.

**Consequences:**
If implemented later:
- Use packet-count fallback only when valid structured RSSI evidence is missing.
- Surface it separately in UI/debug output as `packet activity only`.
- Do not let fallback activity silently masquerade as RSSI-based target confidence.
- Prefer fixing structured Air Unit `EVIDENCE` delivery first.
