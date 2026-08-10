from __future__ import annotations

import asyncio

import flet as ft

from services.audio_service import AudioService


class AnalysisState:
    def __init__(self, page: ft.Page, credit_service, report_service=None):
        self.page = page
        self.credit_service = credit_service
        self.report_service = report_service

        self.content_column = ft.Ref[ft.Column]()
        self.custom_prompt_field = ft.Ref[ft.TextField]()
        self.autopilot_enabled_ref = ft.Ref[ft.Switch]()

        self.is_recording = {"value": False}
        self.is_transcribing = {"value": False}
        self.recording_time = {"value": 0}
        self.recording_timer = ft.Ref[ft.Text]()

        self.loading_file_name = {"value": ""}
        self.loading_file_size = {"value": 0}

        self.analysis_lock = asyncio.Lock()

        self.file_picker_svc = None
        self.audio_svc = AudioService(page)

        self.rebuild_fn = None
        self._disposed = False

        self.pinning_block_index = -1

        self.import_mode = "file"
        self.db_url = ""
        self.db_tables = []
        self.db_selected_table = ""
        self.db_test_status = ""

    def dispose(self):
        """Mark this view state as disposed — all future rebuilds become no-ops."""
        self._disposed = True

    def rebuild(self):
        if self._disposed:
            return
        if self.rebuild_fn:
            self.rebuild_fn()
