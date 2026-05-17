RSSI_MIN_DBM: float = -90.0
RSSI_MAX_DBM: float = -55.0

E_RSSI_WEIGHT: float = 0.5
E_STRONG_WEIGHT: float = 0.3
E_COUNT_WEIGHT: float = 0.2
E_RSSI_P95_WEIGHT: float = 0.6
E_RSSI_MAX_WEIGHT: float = 0.4
E_N_REF: int = 30
E_N_STRONG_REF: int = 10
E_SMOOTHING_BETA: float = 0.3

T_COV_MS: float = 5000.0

T_AGE_MS: float = 300_000.0

# Data freshness
DATA_FRESH_MS: float = 10_000.0
EVIDENCE_FRESH_MS: float = 10_000.0
POSE_DWELL_MAX_MS: float = 2_000.0

D_MAX_M: float = 500.0

R_CHANGE_WEIGHT: float = 0.5
R_FAR_JUMP_WEIGHT: float = 0.5

W_E: float = 0.35
W_U: float = 0.30
W_P: float = 0.20
W_D: float = 0.15
W_R: float = 0.05

W_E_EXPLORE: float = 0.20
W_U_EXPLORE: float = 0.55
W_P_EXPLORE: float = 0.05
W_D_EXPLORE: float = 0.15
W_R_EXPLORE: float = 0.05

W_E_REFINE: float = 0.45
W_U_REFINE: float = 0.15
W_P_REFINE: float = 0.30
W_D_REFINE: float = 0.07
W_R_REFINE: float = 0.03

REFINE_E_THRESHOLD: float = 0.75
REFINE_P_THRESHOLD: float = 0.20
REFINE_PERSIST_WINDOWS: int = 5
REFINE_MAX_DURATION_SEC: float = 15.0

DEFAULT_CELL_SIZE_M: float = 5.0

RECOMMENDATION_INTERVAL_SEC: float = 3.0

GUIDANCE_HISTORY_SUBPATH: str = "guidance/guidance_history.csv"

# Spatial evidence propagation kernel
NEIGHBOR_EVIDENCE_ALPHA_ORTH: float = 0.40
NEIGHBOR_EVIDENCE_ALPHA_DIAG: float = 0.25

# Coverage: frames needed for full packet-based coverage boost
N_COV_PACKET_REF: int = 20

# Ring-2 evidence propagation (only when signal is strong)
STRONG_RSSI_NORM_THRESHOLD: float = 0.70
NEIGHBOR_EVIDENCE_ALPHA_RING2_ORTH: float = 0.12
NEIGHBOR_EVIDENCE_ALPHA_RING2_DIAG: float = 0.07

# Spatial coverage/dwell propagation
NEIGHBOR_COVERAGE_BETA: float = 0.20
NEIGHBOR_COVERAGE_ALPHA_ORTH: float = 1.00
NEIGHBOR_COVERAGE_ALPHA_DIAG: float = 0.70

# Evidence freshness decay (ms); 300 000 ms = 5 min
TAU_EVIDENCE_DECAY_MS: float = 300_000.0

# Minimum evidence for candidate target selection
E_TARGET_MIN: float = 0.05

# Entropy numerics
ENTROPY_EPSILON: float = 1e-6
ENTROPY_MIN_MASS: float = 0.05
