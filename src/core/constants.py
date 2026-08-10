"""Application-wide constants — API config, limits, Colab settings.

Every magic string and hard limit lives here. Import from
``core.constants`` instead of hard-coding values.
"""

from __future__ import annotations

# ── API Gateway (Cloudflare Worker) ─────────────────────────────────
API_BASE_URL = "https://api.spaninsight.com"
API_HEALTH_ENDPOINT = f"{API_BASE_URL}/health"
API_CHAT_ENDPOINT = f"{API_BASE_URL}/chat"

# Headers required by the gateway's security gate
APP_CLIENT_ID = "spaninsight-mobile-v1"
APP_VERSION = "2.0.0"
USER_AGENT = f"SpaninsightApp/{APP_VERSION}"

# ── Task Types (maps to gateway AI ROUTES) ──────────────────────────
TASK_SUGGEST = "suggest"
TASK_CODE = "code"
TASK_INTERPRET = "interpret"
TASK_AUDIO = "audio"
TASK_VISION = "vision"

# ── Audio ───────────────────────────────────────────────────────────
MAX_VOICE_DURATION_SEC = 60
MAX_AUDIO_SIZE_BYTES = 25 * 1024 * 1024  # Gateway limit

# ── Credits ─────────────────────────────────────────────────────────
DAILY_FREE_CREDITS = 50
COST_SUGGEST = 1
COST_CUSTOM_PROMPT = 3
COST_AUTOPILOT = 15

# ── Colab Defaults ──────────────────────────────────────────────────
COLAB_DEFAULT_TIMEOUT = 60.0  # Default code execution timeout (seconds)
COLAB_CONTENT_DIR = "/content"  # Default working directory on Colab
COLAB_UPLOAD_MAX_MB = 100  # Max single file upload size to Colab

# ── Storage Keys (for local persistence) ────────────────────────────
STORAGE_UUID = "spaninsight_uuid"
STORAGE_THEME = "spaninsight.theme"
STORAGE_CREDITS = "spaninsight_credits"
STORAGE_LAST_RESET = "spaninsight_last_reset"
STORAGE_ONBOARDING_DONE = "spaninsight_onboarding_done"
STORAGE_NOTEBOOKS = "spaninsight_notebooks"
STORAGE_ACTIVE_SESSION = "spaninsight_active_session"
STORAGE_DEFAULT_GPU = "spaninsight_default_gpu"
STORAGE_DEFAULT_TPU = "spaninsight_default_tpu"
STORAGE_DEFAULT_TIMEOUT = "spaninsight_default_timeout"
STORAGE_KEEP_ALIVE = "spaninsight_keep_alive"

# ── Network ─────────────────────────────────────────────────────────
ERR_NETWORK = "No internet connection. Please check your network and try again."

# ── Hardware Options ────────────────────────────────────────────────
GPU_OPTIONS = [
    ("", "None (CPU)"),
    ("T4", "T4 · Free"),
    ("L4", "L4 · Pro"),
    ("G4", "G4 · Pro"),
    ("A100", "A100 · Pro+"),
    ("H100", "H100 · Pro+"),
]
TPU_OPTIONS = [
    ("", "None"),
    ("v5e1", "v5e1 · Free"),
    ("v6e1", "v6e1 · Pro"),
]
TIMEOUT_OPTIONS = [15, 30, 60, 120, 300, 600]

# ── File Extensions ─────────────────────────────────────────────────
ALLOWED_EXTENSIONS = [
    "csv",
    "xlsx",
    "xls",
    "json",
    "parquet",
    "feather",
    "tsv",
    "txt",
    "dta",
    "sav",
    "sas7bdat",
    "h5",
    "hdf5",
]
