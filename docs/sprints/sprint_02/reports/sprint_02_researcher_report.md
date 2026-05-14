# [RESEARCHER] Sprint 02 Researcher Report

## Summary

Created `docs/sprints/sprint_02/researcher_constants.md` with the requested five sections: Re-ID scoring weights, Re-ID temporal/sequence parameters, localization constants, enrichment constants, and founder decisions.

## Key Findings

- Legacy Re-ID scoring weights are mostly clear in `reid/models.py`: IE fingerprint `0.75`, frame length `0.20`, SSID bonus `0.10`, sequence bonus `0.05`, IE similarity threshold `0.90`, match threshold `0.80`.
- Legacy Re-ID fingerprints IE tags `1, 50, 45, 127, 221`.
- Legacy PCAP extraction writes `ie_fingerprint` as `TAG:HEX;TAG:HEX;...`, and legacy Re-ID parses exactly that format. The new backend currently writes `TAG:LENGTH|TAG:LENGTH`, so this is a compatibility mismatch.
- Legacy localization RANSAC defaults are clear: `100` iterations, `10.0 dBm` inlier threshold, `3` min samples, early exit at `0.8` inlier ratio.
- Legacy enrichment uses a `1000 ms` merge tolerance. A score threshold equivalent to new `_ENR_01_MATCH_THRESHOLD` was not found.

## Surprises / Source Gaps

- The required `reference/legacy_app/ground_station/reid/pairing.py` source file is missing. Only `pairing.pyc` exists.
- `IMPLEMENTATION_SUMMARY.py` mentions `group_bursts`, `t_max_sec`, `seq_max_gap`, and `min_score`, but the checked source files do not consistently define those as dataclass fields.
- Legacy sequence logic conflicts across sources: code uses `delta < 128`, summary/examples mention `seq_max_gap=50`, and the project PDF describes Bleach around `64`.
- Legacy localization confidence cutoff is not a direct named constant. `vis_thresh = 0.5` appears in calibration/session params, while sprint-02 requests `0.40`.
- New enrichment does not preserve IE hex bytes in `ie_fingerprint`; it writes IE lengths. That blocks faithful Bleach IE similarity scoring until fixed.

## Recommended Next Step

Before production code changes, founder should resolve the decisions in Section 5 of `researcher_constants.md`, especially sequence gap (`50` vs `64` vs `128`), localization confidence cutoff (`0.40` vs `0.50`), enrichment match threshold behavior, and whether to make enrichment emit legacy-compatible IE hex fingerprints as the next backend task.
