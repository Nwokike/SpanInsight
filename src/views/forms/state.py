from dataclasses import dataclass, field

import flet as ft


@dataclass
class FormsState:
    # Dashboard Refs
    content_column: ft.Ref[ft.Column] = field(default_factory=ft.Ref)
    form_prompt_field: ft.Ref[ft.TextField] = field(default_factory=ft.Ref)
    recording_timer: ft.Ref[ft.Text] = field(default_factory=ft.Ref)
    dashboard_container_ref: ft.Ref[ft.Container] = field(default_factory=ft.Ref)
    editor_container_ref: ft.Ref[ft.Container] = field(default_factory=ft.Ref)
    detail_container_ref: ft.Ref[ft.Container] = field(default_factory=ft.Ref)
    user_forms_column_ref: ft.Ref[ft.Column] = field(default_factory=ft.Ref)
    dashboard_progress_bar_ref: ft.Ref[ft.ProgressBar] = field(default_factory=ft.Ref)
    dashboard_voice_button_ref: ft.Ref[ft.IconButton] = field(default_factory=ft.Ref)
    dashboard_send_button_ref: ft.Ref[ft.IconButton] = field(default_factory=ft.Ref)

    # Editor Refs
    editor_recording_timer: ft.Ref[ft.Text] = field(default_factory=ft.Ref)

    # State values
    user_forms: list[dict] = field(default_factory=list)
    is_loading: dict = field(default_factory=lambda: {"value": False})
    is_creating: dict = field(default_factory=lambda: {"value": False})
    is_publishing: dict = field(default_factory=lambda: {"value": False})
    is_recording: dict = field(default_factory=lambda: {"value": False})
    recording_time: dict = field(default_factory=lambda: {"value": 0})
    active_form: dict = field(default_factory=lambda: {"data": None})

    # Editor state
    draft_schema: list[dict] = field(default_factory=list)
    draft_title: dict = field(default_factory=lambda: {"value": ""})
    draft_desc: dict = field(default_factory=lambda: {"value": ""})
    editor_active: dict = field(default_factory=lambda: {"value": False})
    is_transcribing: dict = field(default_factory=lambda: {"value": False})
    prompt_text: dict = field(default_factory=lambda: {"value": ""})

    is_ai_editing: dict = field(default_factory=lambda: {"value": False})
    editor_recording: dict = field(default_factory=lambda: {"value": False})
    editor_transcribing: dict = field(default_factory=lambda: {"value": False})
    editor_recording_time: dict = field(default_factory=lambda: {"value": 0})
    ai_edit_text: dict = field(default_factory=lambda: {"value": ""})
