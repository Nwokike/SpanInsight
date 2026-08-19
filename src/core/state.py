"""Observable application state - single source of truth.

Uses ``@ft.observable`` so Flet can auto-react
to property changes without manual page.update() calls.
"""

from __future__ import annotations

import logging
from typing import Any

import flet as ft

logger = logging.getLogger(__name__)


@ft.observable
class AppState:
    """Global mutable state for Spaninsight v2."""

    # ── Identity ────────────────────────────────────────────────────
    user_uuid: str = ""
    active_project_id: str = ""

    # ── Colab Session ───────────────────────────────────────────────
    active_session_name: str = ""
    active_sessions: list = None  # [{name, endpoint, accelerator, variant, ...}]
    colab_connected: bool = False
    colab_authenticated: bool = False
    is_authenticated: bool = False
    auth_email: str = ""
    session_hardware: str = "CPU"  # CPU, T4, A100, TPU, etc.
    auth_method: str = "oauth2"
    default_gpu: str = ""
    default_tpu: str = ""
    default_timeout: int = 120
    keep_alive_enabled: bool = True

    # ── Notebook ────────────────────────────────────────────────────
    notebook_cells: list[dict] = None  # [{id, type, source, outputs, is_running}]
    current_notebook_name: str = ""
    # Cross-screen handoff: Files → Analysis full import pipeline
    pending_dataset_load: dict = None  # {"remote_path": str, "name": str}

    # ── Credits ─────────────────────────────────────────────────────
    credits_remaining: int = 50
    bonus_credits: int = 0
    last_credit_reset: str = ""

    # ── Forms (kept from v1) ────────────────────────────────────────
    forms: list[dict] = None

    # ── Projects ────────────────────────────────────────────────────
    active_project_name: str = ""
    active_project_dataset: str = ""
    projects_list: list[dict] = None
    user_projects: dict = None

    # ── Reports ─────────────────────────────────────────────────────
    user_reports: list[dict] = None

    # ── AI / Analysis State ─────────────────────────────────────────
    suggestions: list[dict] = None
    active_schema_json: dict = None  # synced by AnalysisScreen for cross-module use
    analysis_blocks: list = None
    is_analyzing: bool = False
    analysis_stage: int = (
        0  # 0=idle, 1=schema, 2=reasoning, 3=code, 4=executing, 5=narrating, 6=healing
    )
    analysis_stage_text: str = ""
    autopilot_enabled: bool = True
    autopilot_cancelled: bool = False
    autopilot_running: bool = False
    autopilot_progress: str = ""
    autopilot_steps: list[dict] = None

    # ── Dataset ─────────────────────────────────────────────────────
    current_df: Any = None  # pandas DataFrame
    current_df_name: str = ""
    current_df_rows: int = 0
    current_df_columns: list = None
    dataset_modified: bool = False

    # ── Navigation & UI ─────────────────────────────────────────────
    current_tab: int = 0  # 0=Home, 1=Analysis, 2=Forms, 3=Reports, 4=Settings
    active_subview: str = ""  # e.g. "projects"
    is_loading: bool = False
    is_online: bool = True
    app_ready: bool = False  # False until _initial_route completes
    gateway_online: bool = True
    trigger_file_picker: bool = False
    onboarding_done: bool = False
    theme_mode: Any = None  # ft.ThemeMode value

    # ── Files (Colab file manager) ──────────────────────────────────
    current_path: str = "/content"
    file_listing: list[dict] = None

    def __init__(self):
        self.notebook_cells = []
        self.pending_dataset_load = None
        self.active_sessions = []
        self.forms = []
        self.projects_list = []
        self.user_projects = {}
        self.user_reports = []
        self.suggestions = []
        self.active_schema_json = {}
        self.analysis_blocks = []
        self.current_df_columns = []
        self.file_listing = []
        self.autopilot_steps = []

    def clear_notebook(self):
        """Reset notebook state for a new session."""
        self.notebook_cells = []
        self.current_notebook_name = ""
        self.active_project_dataset = ""
        self.current_df = None
        self.current_df_name = ""
        self.current_df_rows = 0
        self.current_df_columns = []
        self.suggestions = []
        self.autopilot_progress = ""

    def load_project(self, project: dict):
        """Load a project entity into active state."""
        self.active_project_id = project.get("id", "")
        self.active_project_name = project.get("name", "")
        self.active_project_dataset = project.get("primary_dataset") or project.get(
            "dataset_name", ""
        )
        self.notebook_cells = list(project.get("notebook_cells", []))
        self.suggestions = list(project.get("schema_json", {}).get("suggestions", []))
        self.current_df = None
        self.current_df_name = ""
        self.current_df_rows = 0
        self.current_df_columns = []
        if project.get("hardware"):
            self.session_hardware = project["hardware"]
        if project.get("session_name"):
            self.active_session_name = project["session_name"]

    def add_cell(self, cell_type: str = "code", source: str = "") -> dict:
        """Add a new cell to the notebook."""
        import uuid

        cell = {
            "id": str(uuid.uuid4()),
            "type": cell_type,
            "source": source,
            "outputs": [],
            "is_running": False,
        }
        self.notebook_cells.append(cell)
        return cell


# Module-level singleton
state = AppState()
