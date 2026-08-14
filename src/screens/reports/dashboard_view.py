"""Reports dashboard view displaying saved reports, refresh button, empty state, and sponsored ads."""

from __future__ import annotations

import flet as ft

from components.brand_header import build_brand_header
from components.refresh_button import build_refresh_button
from core import theme, utils
from screens.reports.report_card import build_report_card


def build_reports_dashboard(
    page: ft.Page,
    user_reports: list[dict],
    is_loading: bool,
    on_refresh,
    on_open_report,
    on_start_analysis,
) -> ft.Control:
    """Dashboard view listing all saved analytical reports with quick start CTA."""
    controls = []
    controls.append(build_brand_header(show_tagline=True, spacing_below=True))
    controls.append(
        ft.Container(
            content=ft.Row(
                [
                    ft.Text("Your Reports", size=18, weight=ft.FontWeight.W_700),
                    ft.Container(expand=True),
                    build_refresh_button(on_click=on_refresh),
                ],
            ),
            padding=ft.Padding(20, 10, 20, 0),
        )
    )

    is_mobile = (
        page.platform in (ft.PagePlatform.ANDROID, ft.PagePlatform.IOS)
        if page
        else False
    )

    def _ad():
        if not is_mobile:
            return ft.Container()
        return ft.Container(
            content=ft.Column(
                [
                    ft.Text(
                        "SPONSORED",
                        size=8,
                        weight=ft.FontWeight.W_700,
                        color=ft.Colors.ON_SURFACE_VARIANT,
                        style=ft.TextStyle(letter_spacing=1),
                    ),
                    utils.get_banner_ad(),
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

    controls.append(_ad())

    # Build reports list
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
                            color=ft.Colors.with_opacity(0.15, ft.Colors.ON_SURFACE),
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
                            on_click=on_start_analysis,
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
                    content=build_report_card(report, on_open_report),
                    margin=ft.Margin(20, 4, 20, 4),
                )
            )

    controls.append(ft.Column(controls=reports_list_controls))
    controls.append(_ad())
    controls.append(ft.Container(height=100))

    return ft.Column(controls=controls, scroll="auto", expand=True)
