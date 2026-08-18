"""ReportsScreen — Modular Report generation, editor, and sharing dashboard."""

from __future__ import annotations

import flet as ft

from components.report_editor import build_report_editor
from screens.reports import handlers
from screens.reports.arranger_view import build_arranger_view
from screens.reports.dashboard_view import build_reports_dashboard
from services.audio_service import AudioService
from services.report_service import ReportService
from state import AppStateCtx
from state.controller_ctx import ControllerMethodsCtx
from state.service_ctx import ServiceCtx


class ValueProxy:
    def __init__(self, get_val, set_val):
        self.get_val = get_val
        self.set_val = set_val

    def __getitem__(self, key):
        if key == "value":
            return self.get_val()
        return None

    def __setitem__(self, key, val):
        if key == "value":
            self.set_val(val)


class ListProxy:
    def __init__(self, get_val, set_val):
        self.get_val = get_val
        self.set_val = set_val

    def __iter__(self):
        return iter(self.get_val())

    def __len__(self):
        return len(self.get_val())

    def __getitem__(self, i):
        return self.get_val()[i]

    def set(self, items):
        self.set_val(list(items))

    def clear(self):
        self.set_val([])

    def extend(self, items):
        self.set_val(self.get_val() + list(items))

    def append(self, item):
        self.set_val(self.get_val() + [item])

    def copy(self):
        return self.get_val().copy()


class DictProxy:
    def __init__(self, get_val, set_val):
        self.get_val = get_val
        self.set_val = set_val

    def __getitem__(self, key):
        return self.get_val().get(key)

    def __setitem__(self, key, val):
        d = self.get_val().copy()
        d[key] = val
        self.set_val(d)


class UIStateAdapter:
    def __init__(self):
        self.rebuild = lambda: None


@ft.component
def ReportsScreen() -> ft.Control:
    """Reports screen routing between dashboard, AI arranger, and rich report editor."""
    ft.use_context(AppStateCtx)
    services = ft.use_context(ServiceCtx)
    controller = ft.use_context(ControllerMethodsCtx)
    page = ft.context.page

    # Service instances
    report_service = ft.use_memo(
        lambda: ReportService(services.storage), [services.storage]
    )
    audio_svc = ft.use_memo(lambda: AudioService(page), [page])

    # State hooks
    user_reports, set_user_reports = ft.use_state([])
    active_report, set_active_report = ft.use_state({"data": None})
    editor_blocks, set_editor_blocks = ft.use_state([])
    draft_title, set_draft_title = ft.use_state("")
    draft_desc, set_draft_desc = ft.use_state("")
    is_loading, set_is_loading = ft.use_state(True)
    is_saving, set_is_saving = ft.use_state(False)
    is_sharing, set_is_sharing = ft.use_state(False)
    is_viewing_live, set_is_viewing_live = ft.use_state(False)
    is_deleting, set_is_deleting = ft.use_state(False)
    is_arranging, set_is_arranging = ft.use_state(False)
    is_ai_editing, set_is_ai_editing = ft.use_state(False)
    is_recording, set_is_recording = ft.use_state(False)
    is_transcribing, set_is_transcribing = ft.use_state(False)
    ai_prompt_text, set_ai_prompt_text = ft.use_state("")
    recording_time, set_recording_time = ft.use_state(0)
    is_public, set_is_public = ft.use_state(False)
    editor_active, set_editor_active = ft.use_state(False)

    # Refs
    recording_timer_ref = ft.use_ref()
    save_btn_ref = ft.use_ref()
    share_btn_ref = ft.use_ref()
    view_live_btn_ref = ft.use_ref()

    # Create UIState Adapter for handlers
    ui_state = ft.use_memo(lambda: UIStateAdapter(), [])
    ui_state.is_loading = ValueProxy(lambda: is_loading, set_is_loading)
    ui_state.is_saving = ValueProxy(lambda: is_saving, set_is_saving)
    ui_state.is_sharing = ValueProxy(lambda: is_sharing, set_is_sharing)
    ui_state.is_viewing_live = ValueProxy(lambda: is_viewing_live, set_is_viewing_live)
    ui_state.is_deleting = ValueProxy(lambda: is_deleting, set_is_deleting)
    ui_state.is_arranging = ValueProxy(lambda: is_arranging, set_is_arranging)
    ui_state.is_ai_editing = ValueProxy(lambda: is_ai_editing, set_is_ai_editing)
    ui_state.is_recording = ValueProxy(lambda: is_recording, set_is_recording)
    ui_state.is_transcribing = ValueProxy(lambda: is_transcribing, set_is_transcribing)
    ui_state.ai_prompt_text = ValueProxy(lambda: ai_prompt_text, set_ai_prompt_text)
    ui_state.recording_time = ValueProxy(lambda: recording_time, set_recording_time)
    ui_state.is_public = ValueProxy(lambda: is_public, set_is_public)
    ui_state.editor_active = ValueProxy(lambda: editor_active, set_editor_active)
    ui_state.draft_title = ValueProxy(lambda: draft_title, set_draft_title)
    ui_state.draft_desc = ValueProxy(lambda: draft_desc, set_draft_desc)

    ui_state.user_reports = ListProxy(lambda: user_reports, set_user_reports)
    ui_state.editor_blocks = ListProxy(lambda: editor_blocks, set_editor_blocks)
    ui_state.active_report = DictProxy(lambda: active_report, set_active_report)
    ui_state.audio_svc = audio_svc

    ui_state.recording_timer_ref = recording_timer_ref
    ui_state.save_btn_ref = save_btn_ref
    ui_state.share_btn_ref = share_btn_ref
    ui_state.view_live_btn_ref = view_live_btn_ref

    # Mount effect
    async def _on_mount():
        if page:
            await handlers.load_reports(page, ui_state, report_service)

    ft.use_effect(_on_mount, [])

    def _on_start_analysis(e=None):
        if controller:
            controller.navigate_tab(1)
        else:
            from core.state import state as _st

            _st.current_tab = 1

    show_arranger = is_arranging
    show_editor = editor_active and not show_arranger
    show_dashboard = not show_editor and not show_arranger

    def _handle_public_changed(v):
        set_is_public(v)
        if active_report["data"]:
            d = active_report.copy()
            d["data"]["is_public"] = v
            set_active_report(d)
        if page:
            page.run_task(
                handlers.on_toggle_featured, page, ui_state, report_service, v
            )

    return ft.Column(
        controls=[
            ft.Container(
                visible=show_dashboard,
                content=build_reports_dashboard(
                    page=page,
                    user_reports=user_reports,
                    is_loading=is_loading,
                    on_refresh=lambda e: (
                        page.run_task(
                            handlers.load_reports, page, ui_state, report_service
                        )
                        if page
                        else None
                    ),
                    on_open_report=lambda r: (
                        page.run_task(
                            handlers.on_open_report, page, ui_state, r, report_service
                        )
                        if page
                        else None
                    ),
                    on_start_analysis=_on_start_analysis,
                )
                if show_dashboard
                else None,
                expand=True,
            ),
            ft.Container(
                visible=show_editor,
                content=ft.Column(
                    controls=(
                        build_report_editor(
                            blocks=editor_blocks,
                            title=draft_title,
                            description=draft_desc,
                            on_blocks_changed=set_editor_blocks,
                            on_title_changed=set_draft_title,
                            on_desc_changed=set_draft_desc,
                            on_save=lambda: (
                                page.run_task(
                                    handlers.on_save, page, ui_state, report_service
                                )
                                if page
                                else None
                            ),
                            on_share=lambda: (
                                page.run_task(
                                    handlers.on_share,
                                    page,
                                    ui_state,
                                    report_service,
                                    None,
                                )
                                if page
                                else None
                            ),
                            on_view_live=lambda: (
                                page.run_task(
                                    handlers.on_view_live,
                                    page,
                                    ui_state,
                                    report_service,
                                    None,
                                )
                                if page
                                else None
                            ),
                            on_back=lambda: handlers.on_back(
                                page, ui_state, report_service
                            ),
                            on_import=lambda: (
                                page.run_task(handlers.on_import, page, ui_state)
                                if page
                                else None
                            ),
                            on_ai_edit=lambda action, text: (
                                page.run_task(
                                    handlers.on_ai_edit, page, ui_state, action, text
                                )
                                if page
                                else None
                            ),
                            on_voice_toggle=lambda e: (
                                page.run_task(handlers.on_voice_toggle, page, ui_state)
                                if page
                                else None
                            ),
                            is_saving=is_saving,
                            is_sharing=is_sharing,
                            is_viewing_live=is_viewing_live,
                            is_deleting=is_deleting,
                            is_recording=is_recording,
                            is_transcribing=is_transcribing,
                            is_ai_editing=is_ai_editing,
                            is_public=is_public,
                            on_public_changed=_handle_public_changed,
                            recording_time=recording_time,
                            ai_prompt_text=ai_prompt_text,
                            recording_timer_ref=recording_timer_ref,
                            on_delete=lambda: (
                                page.run_task(
                                    handlers.on_delete_report,
                                    page,
                                    ui_state,
                                    active_report["data"]["id"],
                                    report_service,
                                )
                                if active_report["data"] and page
                                else None
                            ),
                            save_btn_ref=save_btn_ref,
                            share_btn_ref=share_btn_ref,
                            view_live_btn_ref=view_live_btn_ref,
                        )
                        if show_editor
                        else []
                    ),
                    scroll=ft.ScrollMode.AUTO,
                ),
                expand=True,
            ),
            ft.Container(
                visible=show_arranger,
                content=build_arranger_view(page) if show_arranger else None,
                expand=True,
            ),
        ],
        expand=True,
    )
