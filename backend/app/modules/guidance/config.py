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

T_AGE_MS: float = 30_000.0

D_MAX_M: float = 500.0

R_CHANGE_WEIGHT: float = 0.5
R_FAR_JUMP_WEIGHT: float = 0.5

W_E: float = 0.35
W_U: float = 0.30
W_P: float = 0.20
W_D: float = 0.15
W_R: float = 0.05

W_E_EXPLORE: float = 0.20
W_U_EXPLORE: float = 0.50
W_P_EXPLORE: float = 0.10
W_D_EXPLORE: float = 0.15
W_R_EXPLORE: float = 0.05

W_E_REFINE: float = 0.45
W_U_REFINE: float = 0.15
W_P_REFINE: float = 0.30
W_D_REFINE: float = 0.07
W_R_REFINE: float = 0.03

REFINE_E_THRESHOLD: float = 0.65
REFINE_P_THRESHOLD: float = 0.20
REFINE_PERSIST_WINDOWS: int = 3
REFINE_MAX_DURATION_SEC: float = 30.0

DEFAULT_CELL_SIZE_M: float = 30.0

RECOMMENDATION_INTERVAL_SEC: float = 3.0

GUIDANCE_HISTORY_SUBPATH: str = "guidance/guidance_history.csv"
