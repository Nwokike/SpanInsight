"""Reports view layout and UI builder."""

from __future__ import annotations

from datetime import UTC, datetime

import flet as ft

from components.brand_header import build_brand_header
from components.refresh_button import build_refresh_button
from components.report_editor import build_report_editor
from core import theme, utils

from . import handlers
from .state import ReportsState


def build_report_view(
    page: ft.Page,
    report_service=None,
    ad_service=None,
    storage=None,
    credit_service=None,
) -> ft.View:
    ui_state = ReportsState(page)

    async def _on_start_analysis(e):
        await page.push_route("/analysis")

    def _rebuild():
        if not ui_state.content_column.current:
            return

        # Determine which layer should be visible
        show_arranger = ui_state.is_arranging["value"]
        show_editor = ui_state.editor_active["value"] and not show_arranger
        show_dashboard = not show_editor and not show_arranger

        # Toggle Visibilities without destroying existing DOM elements
        for ref, vis in [
            (ui_state.dashboard_container_ref, show_dashboard),
            (ui_state.editor_container_ref, show_editor),
            (ui_state.arranger_overlay_ref, show_arranger),
        ]:
            if ref.current and ref.current.visible != vis:
                ref.current.visible = vis
                ref.current.update()

        # Targeted updates for active layers
        if show_dashboard and ui_state.dashboard_container_ref.current:
            _update_dashboard_reports()

        if show_editor and ui_state.editor_container_ref.current:
            # We assign content here ONLY when actually structural block changes occur.
            # State updates (saving, sharing) will be handled via refs directly in handlers.
            ui_state.editor_container_ref.current.content = ft.Column(
                controls=build_report_editor(
                    blocks=ui_state.editor_blocks,
                    title=ui_state.draft_title["value"],
                    description=ui_state.draft_desc["value"],
                    on_blocks_changed=_rebuild,
                    on_title_changed=lambda v: ui_state.draft_title.update(
                        {"value": v}
                    ),
                    on_desc_changed=lambda v: ui_state.draft_desc.update({"value": v}),
                    on_save=lambda: page.run_task(
                        handlers.on_save, page, ui_state, report_service
                    ),
                    on_share=lambda: page.run_task(
                        handlers.on_share, page, ui_state, report_service, ad_service
                    ),
                    on_view_live=lambda: page.run_task(
                        handlers.on_view_live,
                        page,
                        ui_state,
                        report_service,
                        ad_service,
                    ),
                    on_back=lambda: handlers.on_back(page, ui_state, report_service),
                    on_import=lambda: handlers.on_import(page, ui_state),
                    on_ai_edit=lambda action, text: page.run_task(
                        handlers.on_ai_edit, page, ui_state, action, text
                    ),
                    on_voice_toggle=lambda e: page.run_task(
                        handlers.on_voice_toggle, page, ui_state
                    ),
                    is_saving=ui_state.is_saving["value"],
                    is_sharing=ui_state.is_sharing["value"],
                    is_viewing_live=ui_state.is_viewing_live["value"],
                    is_deleting=ui_state.is_deleting["value"],
                    is_recording=ui_state.is_recording["value"],
                    is_transcribing=ui_state.is_transcribing["value"],
                    is_ai_editing=ui_state.is_ai_editing["value"],
                    is_public=ui_state.is_public["value"],
                    on_public_changed=lambda v: (
                        ui_state.is_public.update({"value": v}),
                        ui_state.active_report["data"].__setitem__("is_public", v)
                        if ui_state.active_report["data"]
                        else None,
                        _rebuild(),
                    ),
                    recording_time=ui_state.recording_time["value"],
                    ai_prompt_text=ui_state.ai_prompt_text["value"],
                    recording_timer_ref=ui_state.recording_timer_ref,
                    on_delete=lambda: (
                        page.run_task(
                            handlers.on_delete_report,
                            page,
                            ui_state,
                            ui_state.active_report["data"]["id"],
                            report_service,
                        )
                        if ui_state.active_report["data"]
                        else None
                    ),
                    # Pass the targeted component Refs down to stop laggy UI updates
                    save_btn_ref=ui_state.save_btn_ref,
                    share_btn_ref=ui_state.share_btn_ref,
                    view_live_btn_ref=ui_state.view_live_btn_ref,
                )
            )
            ui_state.editor_container_ref.current.update()

    ui_state.rebuild_fn = _rebuild

    def _update_dashboard_reports():
        """Updates just the list of reports dynamically without rebuilding headers."""
        if not ui_state.user_reports_column_ref.current:
            return

        controls = []
        if ui_state.is_loading["value"]:
            controls.append(
                ft.Container(
                    content=ft.Column(
                        [ft.ProgressRing(width=30, height=30, stroke_width=3)],
                        horizontal_alignment="center",
                    ),
                    padding=40,
                    alignment=ft.Alignment.CENTER,
                )
            )
        elif not ui_state.user_reports:
            controls.append(
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
            for report in ui_state.user_reports:
                controls.append(
                    ft.Container(
                        content=_build_report_card(report),
                        margin=ft.Margin(20, 4, 20, 4),
                    )
                )

        ui_state.user_reports_column_ref.current.controls = controls
        ui_state.user_reports_column_ref.current.update()

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

    def _build_dashboard_layout() -> list[ft.Control]:
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

        # The dynamically populated reports list placeholder
        controls.append(ft.Column(ref=ui_state.user_reports_column_ref, controls=[]))

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
        return controls

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

    page.run_task(handlers.load_reports, page, ui_state, report_service)

    return ft.View(
        route="/reports",
        appbar=ft.AppBar(
            title=ft.Text("Reports", weight="bold"),
            bgcolor=ft.Colors.TRANSPARENT,
        ),
        controls=[
            ft.Column(
                ref=ui_state.content_column,
                controls=[
                    ft.Container(
                        ref=ui_state.dashboard_container_ref,
                        visible=True,
                        content=ft.Column(
                            _build_dashboard_layout(), scroll="auto", expand=True
                        ),
                    ),
                    ft.Container(
                        ref=ui_state.editor_container_ref,
                        visible=False,
                        content=ft.Column(),
                    ),
                    ft.Container(
                        ref=ui_state.arranger_overlay_ref,
                        visible=False,
                        content=_build_arranger_layout(),
                    ),
                ],
                scroll="auto",
                expand=True,
            ),
        ],
        padding=0,
    )
