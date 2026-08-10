"""Notebook view state — tracks per-view mutable state for the notebook."""

from __future__ import annotations

import asyncio

import flet as ft


class NotebookState:
    """Per-view mutable state for the notebook view.

    Similar to v1's AnalysisState but wired for Colab execution
    instead of local sandbox.
    """

    def __init__(self, page: ft.Page, colab_service, credit_service, storage):
        self.page = page
        self.colab_service = colab_service
        self.credit_service = credit_service
        self.storage = storage

        # UI references
        self.content_column = ft.Ref[ft.Column]()
        self.custom_prompt_field = ft.Ref[ft.TextField]()
        self.autopilot_enabled_ref = ft.Ref[ft.Switch]()

        # Voice recording state
        self.is_recording = {"value": False}
        self.is_transcribing = {"value": False}
        self.recording_time = {"value": 0}
        self.recording_timer = ft.Ref[ft.Text]()

        # File upload state
        self.loading_file_name = {"value": ""}
        self.loading_file_size = {"value": 0}

        # Execution lock — prevents concurrent AI calls
        self.analysis_lock = asyncio.Lock()

        self.file_picker_svc = None

        # Audio service (if available)
        try:
            from services.audio_service import AudioService

            self.audio_svc = AudioService(page)
        except Exception:
            self.audio_svc = None

        self.rebuild_fn = None
        self._disposed = False

        # Input mode toggle
        self.terminal_expanded = False  # False = prompt mode, True = code mode

    def dispose(self):
        """Mark this view state as disposed — all future rebuilds become no-ops."""
        self._disposed = True

    def rebuild(self):
        if self._disposed or self.page.route != "/notebook":
            return
        if self.rebuild_fn:
            self.rebuild_fn()
