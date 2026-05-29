export const HELP = {
  score_containment:
    'Fraction of matched GT points whose known location falls inside the cluster uncertainty radius. Rewards accurate uncertainty estimation. Weight: 40%.',
  score_distance:
    'How close cluster peaks are to their matched GT points. Below the free zone = 100%. Score drops quadratically for larger errors. Weight: 30%.',
  score_count:
    'Fraction of GT points that were matched (recall). 100% = every known device was found, regardless of how many extra clusters exist. Weight: 20%.',
  score_radius:
    'Rewards tight (small) uncertainty radii. Below the free zone = 100%. Larger radii score lower. Weight: 10%. Note: radii are not yet calibrated - treat as indicative.',
  recall: 'Fraction of GT points matched to a cluster. High recall means few devices were missed.',
  precision: 'Fraction of predicted clusters matched to a GT point. High precision means few false alarms.',
  coverage: 'Fraction of matched GT points whose known location falls inside the cluster uncertainty circle.',
  median_error: 'Middle value of the distance between matched GT points and their cluster peaks, in metres.',
  p90_error: '90th percentile of match distances. 90% of matched devices were found within this many metres.',
  count_error:
    'Predicted clusters minus GT points. Positive = more clusters than expected (over-detection). Negative = fewer (under-detection).',
  false_positives:
    'Clusters not matched to any GT point. These are phantom detections - noise, interference, or one real device split into extra clusters. Every false positive wastes search time.',
  false_negatives:
    'GT points with no cluster assigned to them - the system did not find these devices. The most critical failures in a SAR mission.',
  duplicates:
    'Unmatched clusters that are still close to a GT already claimed by another cluster. Usually caused by Re-ID splitting one real device into multiple clusters. Fix by increasing the Re-ID association threshold.',
  ambiguous_gt:
    'A GT point where two or more clusters are too similar in distance for a confident assignment. No score contribution. Reduce the ratio gate or rerun with tighter Re-ID params.',
  possible_merge:
    'A cluster within range of two or more GT points. It may have captured signals from multiple devices simultaneously. Consider lowering the Re-ID association threshold to split it.',
  association_clear:
    'The nearest cluster was significantly closer than the second-nearest (ratio gate passed). The match is considered unambiguous.',
  ratio_gate:
    'Ambiguity threshold. The nearest cluster must be this many times closer than the second-nearest to count as a clear match. Lower = more permissive. 1.0 = always match the nearest cluster. 2.0 = strict (rarely matches in dense outputs).',
  max_match_dist_m:
    'A GT point farther than this distance from every cluster is marked a False Negative and excluded from scoring entirely.',
  d_free_m:
    'Distance threshold below which Distance and Radius scores are perfect (100%). Errors within this zone are considered negligible for SAR purposes.',
  r_normalize_m:
    'Scale of the quadratic penalty beyond the free zone. At free zone + this value, the score reaches 0%. Larger = gentler drop for larger errors.',
  w_containment: 'Weight of the Containment sub-score in the total (0-1). All four weights should sum to 1.0.',
  w_distance: 'Weight of the Distance sub-score in the total (0-1).',
  w_count: 'Weight of the Count sub-score in the total (0-1).',
  w_radius: 'Weight of the Radius sub-score in the total (0-1).',
  cluster_confidence:
    "Re-ID's self-assessment of this cluster's reliability, based on detection consistency and signal strength. High = strong, repeated detections. Low = sparse or weak signal.",
  cluster_type_static:
    'Device that did not move during the scan - infrastructure APs, parked vehicles, fixed beacons. Localised but typically not a SAR target.',
  cluster_type_dynamic:
    'Device with mobile or inconsistent presence - likely a phone or temporary emitter. Primary target type in SAR.',
  cluster_type_noise:
    'Detections that could not be assigned to a stable cluster. May be interference, marginal signals, or brief passing devices.',
  uncertainty_radius:
    'The radius of the uncertainty circle around the cluster peak, in metres. The real device is estimated to be within this area.',
  loc_grid_resolution_m:
    'Size of each grid cell in metres. Smaller = finer probability map but slower computation. Typical range: 1-5 m.',
  loc_dynamic_sigma_alpha:
    'Controls how the Gaussian signal spread scales with estimated device distance. Higher = wider kernel per reading, smoother heatmap.',
  loc_confidence_cutoff:
    'Minimum normalised score to include a grid cell in the output heatmap. Higher = only the most confident locations are shown.',
  loc_uncertainty_participation_floor:
    'Minimum relative evidence for a reading to contribute to the uncertainty radius calculation. Filters out weak, distant detections.',
  loc_uncertainty_alpha:
    'Multiplier for the uncertainty radius size. Higher = more conservative (larger) radius estimates.',
  loc_buffer_m: 'How many metres to extend the search area beyond the drone GPS track bounding box.',
  reid_association_threshold:
    'Minimum similarity score (0-1) to link two detections as the same device. Higher = stricter, purer clusters. Lower = more links, risk of merging different devices.',
  reid_seq_gap_max:
    'Maximum number of consecutive missed detections allowed before a device track is split into separate clusters.',
  reid_time_gap_max_sec:
    'Maximum time gap between detections to keep them in the same cluster. A longer gap starts a new cluster.',
  reid_burst_window_sec:
    'Time window for grouping burst detections from the same device. Used to weight repeated rapid transmissions.',
  reid_probe_requests_only:
    'Use only Wi-Fi probe requests for Re-ID, ignoring beacons. Reduces false associations from static access points that broadcast continuously.',
  ground_truth:
    'Known physical locations of target devices, placed manually or imported from a file. Used as reference points to score how well the system found each device.',
  reid_artifact:
    'The Re-ID CSV output used as localization input. Contains clustered, GPS-stamped detections ready for spatial processing.',
  show_static_clusters:
    'Toggle visibility of clusters from fixed devices (APs, infrastructure). These are localised but are typically not SAR targets.',
  show_noise_cluster:
    'Toggle visibility of the noise cluster - detections that did not form any stable cluster.',
  heatmap:
    'Probability density overlay for each cluster. Warmer colours (red/orange) = higher likelihood the device is in that cell.',
  radii:
    'Uncertainty circles around each cluster peak. The real device is estimated to be somewhere within this radius.',
  peaks: 'The single most-probable location for each cluster, shown as a dot on the map.',
  calibration_csv:
    'Scan file used to derive signal propagation parameters. Should be captured at known device-to-drone distances.',
  ransac:
    'Random Sample Consensus - a robust fitting algorithm that identifies and ignores outlier RSSI readings before fitting the path loss model.',
  rssi_at_1m:
    'Expected signal strength at exactly 1 metre distance, in dBm. The anchor point of the path loss model.',
  path_loss_n:
    'Path loss exponent. 2 = free space. 3-4 = urban or obstructed environments. Higher = signal fades faster with distance.',
  calib_sigma:
    'Standard deviation of RSSI residuals after the path loss fit, in dB. Smaller = more consistent measurements, more reliable localisation.',
  r_squared:
    'Goodness of fit (0-1). How well the path loss model explains the observed RSSI variation. Below 0.6 suggests noisy or mixed-environment calibration.',
  inliers:
    'Detections that fit the path loss model within the RANSAC threshold. The model is derived from these only; outliers are ignored.',
  gps_fix:
    'Whether the drone had a valid GPS lock for this reading. Readings without GPS fix have unreliable location data and are less useful for localisation.',
  rssi_range:
    'Signal strength range (minimum to maximum) across all detections in this scan, in dBm. More negative = weaker signal. Typical Wi-Fi: -30 (strong) to -90 (very weak).',
  heartbeats:
    'Periodic GPS-only log entries from the drone with no Wi-Fi scan data. Used to fill in the GPS track.',
  frame_type:
    'Type of Wi-Fi frame captured. Beacon: device advertises itself. Probe-req: device searching for known networks.',
  pcap:
    'Packet capture file recorded by the drone Wi-Fi sniffer. Contains raw Wi-Fi frames that are matched to GPS-stamped scan rows to add protocol-level details.',
  enriched_artifact:
    'The output of the enrichment stage - the original scan CSV with PCAP-matched protocol fields (exact timing, signal details) added to each row.',
  match_rate:
    'Percentage of scan rows successfully matched to a PCAP frame within the time window. Low match rate may indicate a clock sync issue or missing PCAP.',
  static_clusters:
    'Clusters from devices with consistent, fixed-location detections (APs, infrastructure). Counted separately from dynamic clusters.',
  noise_clusters:
    'Detections that could not be assigned to any stable cluster - interference, marginal signals, or brief passing devices.',
  dynamic_clusters:
    'Clusters from devices that moved or had inconsistent presence. Likely mobile phones or temporary emitters. Primary targets in SAR.',
  unique_dynamic_macs:
    'Number of distinct device identities in dynamic clusters. A rough proxy for how many potential targets were detected.',
} as const
