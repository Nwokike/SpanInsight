"""Reports view screen component."""

from datetime import UTC, datetime

import flet as ft

from components.brand_header import build_brand_header
from components.refresh_button import build_refresh_button
from components.report_editor import build_report_editor
from core import theme, utils
from services.audio_service import AudioService
from services.report_service import ReportService
from state import AppStateCtx
from state.controller_ctx import ControllerMethodsCtx
from state.service_ctx import ServiceCtx
from views.reports import handlers


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
    ft.use_context(AppStateCtx)
    services = ft.use_context(ServiceCtx)
    ft.use_context(ControllerMethodsCtx)
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
    # Update adapter on every render to point to latest closures
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

    # Mount effect for initial data load
    def _on_mount():
        page.run_task(handlers.load_reports, page, ui_state, report_service)

    ft.use_effect(_on_mount, [])

    # Navigation handling
    async def _on_start_analysis(e):
        await page.push_route("/analysis")

    # Visibility booleans
    show_arranger = is_arranging
    show_editor = editor_active and not show_arranger
    show_dashboard = not show_editor and not show_arranger

    # Extracted Builders

    def _build_report_card(report: dict) -> ft.Container:
        block_count = len(report.get("blocks", []))
        try:
            dt = datetime.fromtimestamp(report.get("created_at", 0), tz=UTC)
            time_str = dt.strftime("%b %d, %Y")
        except Exception:
            time_str = ""

        return ft.Container(
            content=ft.Row(
                [
                    ft.Container(
                        content=ft.Icon(
                            ft.Icons.ASSESSMENT_ROUNDED,
                            color=theme.PRIMARY,
                            size=24,
                        ),
                        width=44,
                        height=44,
                        border_radius=12,
                        bgcolor=ft.Colors.with_opacity(0.1, theme.PRIMARY),
                        alignment=ft.Alignment.CENTER,
                    ),
                    ft.Column(
                        [
                            ft.Text(
                                report.get("title", "Untitled Report"),
                                weight=ft.FontWeight.W_600,
                                size=14,
                                max_lines=1,
                                overflow="ellipsis",
                            ),
                            ft.Text(
                                f"{block_count} block{'s' if block_count != 1 else ''} · {report.get('dataset_name', '')} · {time_str}",
                                size=11,
                                color=ft.Colors.ON_SURFACE_VARIANT,
                                max_lines=1,
                            ),
                        ],
                        spacing=2,
                        expand=True,
                    ),
                    ft.Row(
                        [
                            ft.Container(
                                content=ft.Text(
                                    "Shared" if report.get("share_url") else "",
                                    size=10,
                                    color=theme.SUCCESS,
                                ),
                                visible=bool(report.get("share_url")),
                            ),
                            ft.Icon(
                                ft.Icons.CHEVRON_RIGHT_ROUNDED,
                                color=ft.Colors.ON_SURFACE_VARIANT,
                            ),
                        ],
                        spacing=4,
                    ),
                ],
                spacing=12,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            padding=14,
            border_radius=14,
            bgcolor=theme.GLASS_BG,
            border=ft.Border.all(1, theme.GLASS_BORDER_COLOR),
            on_click=lambda e, r=report: page.run_task(
                handlers.on_open_report, page, ui_state, r, report_service
            ),
            ink=True,
        )

    def _build_dashboard_layout() -> ft.Control:
        controls = []
        controls.append(build_brand_header(show_tagline=True, spacing_below=True))
        controls.append(
            ft.Container(
                content=ft.Row(
                    [
                        ft.Text("Your Reports", size=18, weight=ft.FontWeight.W_700),
                        ft.Container(expand=True),
                        build_refresh_button(
                            on_click=lambda e: page.run_task(
                                handlers.load_reports, page, ui_state, report_service
                            ),
                        ),
                    ],
                ),
                padding=ft.Padding(20, 10, 20, 0),
            )
        )

        if page.platform in (ft.PagePlatform.ANDROID, ft.PagePlatform.IOS):
            controls.append(
                ft.Container(
                    content=ft.Column(
                        [
                            ft.Text(
                                "SPONSORED",
                                size=8,
                                weight=ft.FontWeight.W_700,
                                color=ft.Colors.ON_SURFACE_VARIANT,
                                style=ft.TextStyle(letter_spacing=1),
                            ),
                            utils.get_banner_ad(
                                unit_id="ca-app-pub-5679949845754640/5628404223",
                                width=320,
                                height=50,
                            ),
                        ],
                        horizontal_alignment="center",
                        spacing=4,
                    ),
                    alignment=ft.Alignment.CENTER,
                    padding=8,
                    border_radius=12,
                    bgcolor=theme.GLASS_BG,
                    border=ft.Border.all(1, theme.GLASS_BORDER_COLOR),
                    margin=ft.Margin(20, 10, 20, 10),
                )
            )

        # Build reports list dynamically
        reports_list_controls = []
        if is_loading:
            reports_list_controls.append(
                ft.Container(
                    content=ft.Column(
                        [ft.ProgressRing(width=30, height=30, stroke_width=3)],
                        horizontal_alignment="center",
                    ),
                    padding=40,
                    alignment=ft.Alignment.CENTER,
                )
            )
        elif not user_reports:
            reports_list_controls.append(
                ft.Container(
                    content=ft.Column(
                        [
                            ft.Container(height=40),
                            ft.Icon(
                                ft.Icons.ASSESSMENT_OUTLINED,
                                size=64,
                                color=ft.Colors.with_opacity(
                                    0.15, ft.Colors.ON_SURFACE
                                ),
                            ),
                            ft.Text(
                                "No reports yet",
                                size=16,
                                weight="w500",
                                color=ft.Colors.ON_SURFACE_VARIANT,
                            ),
                            ft.Text(
                                "Pin analysis results or use Autopilot to create your first report.",
                                size=13,
                                color=ft.Colors.with_opacity(0.5, ft.Colors.ON_SURFACE),
                                text_align="center",
                            ),
                            ft.Container(height=16),
                            ft.FilledButton(
                                "Start Analysis",
                                icon=ft.Icons.ANALYTICS_ROUNDED,
                                style=ft.ButtonStyle(
                                    bgcolor=theme.PRIMARY,
                                    color=ft.Colors.WHITE,
                                    shape=ft.RoundedRectangleBorder(radius=12),
                                    padding=16,
                                ),
                                on_click=_on_start_analysis,
                            ),
                        ],
                        horizontal_alignment="center",
                        spacing=8,
                    ),
                    padding=20,
                    alignment=ft.Alignment.CENTER,
                )
            )
        else:
            for report in user_reports:
                reports_list_controls.append(
                    ft.Container(
                        content=_build_report_card(report),
                        margin=ft.Margin(20, 4, 20, 4),
                    )
                )

        controls.append(ft.Column(controls=reports_list_controls))

        if page.platform in (ft.PagePlatform.ANDROID, ft.PagePlatform.IOS):
            controls.append(
                ft.Container(
                    content=ft.Column(
                        [
                            ft.Text(
                                "SPONSORED",
                                size=8,
                                weight=ft.FontWeight.W_700,
                                color=ft.Colors.ON_SURFACE_VARIANT,
                                style=ft.TextStyle(letter_spacing=1),
                            ),
                            utils.get_banner_ad(
                                unit_id="ca-app-pub-5679949845754640/5628404223",
                                width=320,
                                height=50,
                            ),
                        ],
                        horizontal_alignment="center",
                        spacing=4,
                    ),
                    alignment=ft.Alignment.CENTER,
                    padding=8,
                    border_radius=12,
                    bgcolor=theme.GLASS_BG,
                    border=ft.Border.all(1, theme.GLASS_BORDER_COLOR),
                    margin=ft.Margin(20, 8, 20, 8),
                )
            )

        controls.append(ft.Container(height=100))
        return ft.Column(controls=controls, scroll="auto", expand=True)

    def _build_arranger_layout() -> ft.Control:
        controls = [
            ft.Container(height=80),
            ft.ProgressRing(width=40, height=40, stroke_width=3),
            ft.Text(
                "AI is arranging your report...",
                size=14,
                color=ft.Colors.ON_SURFACE_VARIANT,
            ),
            ft.Text(
                "Optimizing order, polishing descriptions",
                size=12,
                color=ft.Colors.with_opacity(0.5, ft.Colors.ON_SURFACE),
            ),
        ]

        if page.platform in (ft.PagePlatform.ANDROID, ft.PagePlatform.IOS):
            controls.append(
                ft.Container(
                    content=ft.Column(
                        [
                            ft.Text(
                                "SPONSORED",
                                size=8,
                                weight=ft.FontWeight.W_700,
                                color=ft.Colors.ON_SURFACE_VARIANT,
                                style=ft.TextStyle(letter_spacing=1),
                            ),
                            utils.get_banner_ad(
                                unit_id="ca-app-pub-5679949845754640/5628404223",
                                width=320,
                                height=50,
                            ),
                        ],
                        horizontal_alignment="center",
                        spacing=4,
                    ),
                    alignment=ft.Alignment.CENTER,
                    padding=8,
                    border_radius=12,
                    bgcolor=theme.GLASS_BG,
                    border=ft.Border.all(1, theme.GLASS_BORDER_COLOR),
                    margin=ft.Margin(0, 12, 0, 0),
                )
            )

        return ft.Container(
            content=ft.Column(controls, horizontal_alignment="center", spacing=12),
            expand=True,
            alignment=ft.Alignment.CENTER,
        )

    def _handle_public_changed(v):
        set_is_public(v)
        if active_report["data"]:
            d = active_report.copy()
            d["data"]["is_public"] = v
            set_active_report(d)

    return ft.Column(
        controls=[
            ft.Container(
                visible=show_dashboard,
                content=_build_dashboard_layout() if show_dashboard else None,
                expand=True,
            ),
            ft.Container(
                visible=show_editor,
                content=ft.Column(
                    controls=[
                        build_report_editor(
                            blocks=editor_blocks,
                            title=draft_title,
                            description=draft_desc,
                            on_blocks_changed=lambda: None,  # state auto updates
                            on_title_changed=set_draft_title,
                            on_desc_changed=set_draft_desc,
                            on_save=lambda: page.run_task(
                                handlers.on_save, page, ui_state, report_service
                            ),
                            on_share=lambda: page.run_task(
                                handlers.on_share, page, ui_state, report_service, None
                            ),
                            on_view_live=lambda: page.run_task(
                                handlers.on_view_live,
                                page,
                                ui_state,
                                report_service,
                                None,
                            ),
                            on_back=lambda: handlers.on_back(
                                page, ui_state, report_service
                            ),
                            on_import=lambda: handlers.on_import(page, ui_state),
                            on_ai_edit=lambda action, text: page.run_task(
                                handlers.on_ai_edit, page, ui_state, action, text
                            ),
                            on_voice_toggle=lambda e: page.run_task(
                                handlers.on_voice_toggle, page, ui_state
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
                                if active_report["data"]
                                else None
                            ),
                            save_btn_ref=save_btn_ref,
                            share_btn_ref=share_btn_ref,
                            view_live_btn_ref=view_live_btn_ref,
                        )
                    ]
                    if show_editor
                    else []
                ),
                expand=True,
            ),
            ft.Container(
                visible=show_arranger,
                content=_build_arranger_layout() if show_arranger else None,
                expand=True,
            ),
        ],
        expand=True,
    )
