"""Application-wide constants — API config, limits, security.

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
APP_VERSION = "1.2.3"
USER_AGENT = f"SpaninsightApp/{APP_VERSION}"

# ── Task Types (maps to gateway ROUTES) ─────────────────────────────
TASK_SUGGEST = "suggest"
TASK_CODE = "code"
TASK_INTERPRET = "interpret"
TASK_AUDIO = "audio"
TASK_VISION = "vision"

# ── File Limits ─────────────────────────────────────────────────────
# Modern phones have 4GB+ RAM. pandas can handle ~100MB CSVs comfortably.
MAX_FILE_SIZE_MB = 100
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024
ALLOWED_EXTENSIONS = {
    ".csv",
    ".json",
    ".jsonl",
    ".ndjson",
    ".xlsx",
    ".xml",
    ".dta",
    ".sas7bdat",
    ".xport",
    ".tsv",
    ".txt",
    ".pkl",
    ".pickle",
    ".zip",
}

# ── Data Display ────────────────────────────────────────────────────
DATA_PREVIEW_ROWS = 20

# ── Audio ───────────────────────────────────────────────────────────
MAX_VOICE_DURATION_SEC = 60
MAX_AUDIO_SIZE_BYTES = 25 * 1024 * 1024  # Gateway limit

# ── Credits ─────────────────────────────────────────────────────────
DAILY_FREE_CREDITS = 50
COST_SUGGEST = 1
COST_CUSTOM_PROMPT = 3
COST_AUTOPILOT = 15

# ── Sandbox Security ────────────────────────────────────────────────
BLOCKED_TERMS = [
    "import os",
    "import sys",
    "subprocess",
    "open(",
    "shutil",
    "import socket",
    "import http",
    "__import__",
    "eval(",
    "compile(",
    "exec(",
    "import pathlib",
    "import glob",
    "import signal",
    "import ctypes",
    "import multiprocessing",
    "import threading",
    "import asyncio",
    "import requests",
    "import urllib",
    "import webbrowser",
    # Additional bypass prevention
    "getattr(",
    "setattr(",
    "delattr(",
    "importlib",
    "__builtins__",
    "__subclasses__",
    "__globals__",
    "__code__",
    "__class__",
    "breakpoint",
    "import io",
    "import pickle",
    "import marshal",
    "import code",
    # Object introspection bypass vectors
    ".__bases__",
    ".__mro__",
    ".__init__",
    ".__new__",
    ".__reduce__",
    ".__reduce_ex__",
    ".__getattribute__",
    "object()",
    # CF1: type(), hasattr(), dir() are safe introspection functions
    # commonly used by AI-generated pandas code. Removed to avoid
    # false positives. Dangerous access is blocked by the AST checker.
    # Pandas file/network I/O
    "read_pickle",
    "to_pickle",
    "read_sql",
    "to_sql",
    "read_hdf",
    "to_hdf",
    "read_feather",
    "to_feather",
    "read_parquet",
    "to_parquet",
    "read_clipboard",
    "to_clipboard",
    "read_html",
    "read_stata",
    "read_spss",
    "read_sas",
    # NumPy file I/O
    "np.load(",
    "np.save(",
    "np.savetxt(",
    "np.loadtxt(",
]

SANDBOX_TIMEOUT_SEC = 60

# ── Storage Keys (for SecureStorage) ────────────────────────────────
STORAGE_UUID = "spaninsight_uuid"
STORAGE_THEME = "spaninsight.theme"
STORAGE_CREDITS = "spaninsight_credits"
STORAGE_LAST_RESET = "spaninsight_last_reset"
STORAGE_ONBOARDING_DONE = "spaninsight_onboarding_done"
STORAGE_REPORTS = "spaninsight_reports"
