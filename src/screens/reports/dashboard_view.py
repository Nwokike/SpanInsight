"""Reports dashboard view displaying saved reports, refresh button, empty state, and sponsored ads."""

from __future__ import annotations

import flet as ft

from components.brand_header import build_brand_header
from components.refresh_button import build_refresh_button
from core import theme, tokens, utils
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
                    ft.Text(
                        "Your Reports",
                        size=tokens.FONT_LG,
                        weight=ft.FontWeight.W_700,
                    ),
                    ft.Container(expand=True),
                    build_refresh_button(on_click=on_refresh),
                ],
            ),
            padding=ft.Padding(
                tokens.SPACE_XL,
                tokens.SPACE_MD_SM,
                tokens.SPACE_XL,
                tokens.SPACE_NONE,
            ),
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
                        size=tokens.FONT_XXS,
                        weight=ft.FontWeight.W_700,
                        color=ft.Colors.ON_SURFACE_VARIANT,
                        style=ft.TextStyle(letter_spacing=1),
                    ),
                    utils.get_banner_ad(),
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=tokens.SPACE_XS,
            ),
            alignment=ft.Alignment.CENTER,
            padding=tokens.SPACE_SM,
            border_radius=tokens.RADIUS_MD,
            bgcolor=theme.GLASS_BG,
            border=ft.Border.all(tokens.DIVIDER_THICKNESS, theme.GLASS_BORDER_COLOR),
            margin=ft.Margin(
                tokens.SPACE_XL,
                tokens.SPACE_MD_SM,
                tokens.SPACE_XL,
                tokens.SPACE_MD_SM,
            ),
        )

    controls.append(_ad())

    # Build reports list
    reports_list_controls = []
    if is_loading:
        reports_list_controls.append(
            ft.Container(
                content=ft.Column(
                    [
                        ft.ProgressRing(
                            width=tokens.BUTTON_HEIGHT_SM,
                            height=tokens.BUTTON_HEIGHT_SM,
                            stroke_width=tokens.PROGRESS_RING_STROKE_NORMAL,
                        )
                    ],
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                padding=tokens.ICON_CONTAINER_SIZE,
                alignment=ft.Alignment.CENTER,
            )
        )
    elif not user_reports:
        reports_list_controls.append(
            ft.Container(
                content=ft.Column(
                    [
                        ft.Container(height=tokens.ICON_CONTAINER_SIZE),
                        ft.Icon(
                            ft.Icons.ASSESSMENT_OUTLINED,
                            size=tokens.ICON_HERO_LG,
                            color=ft.Colors.with_opacity(
                                tokens.OPACITY_BORDER, ft.Colors.ON_SURFACE
                            ),
                        ),
                        ft.Text(
                            "No reports yet",
                            size=tokens.FONT_HEADING,
                            weight=ft.FontWeight.W_500,
                            color=ft.Colors.ON_SURFACE_VARIANT,
                        ),
                        ft.Text(
                            "Pin analysis results or use Autopilot to create your first report.",
                            size=tokens.FONT_BODY,
                            color=ft.Colors.with_opacity(
                                tokens.OPACITY_HALF, ft.Colors.ON_SURFACE
                            ),
                            text_align=ft.TextAlign.CENTER,
                        ),
                        ft.Container(height=tokens.SPACE_LG),
                        ft.FilledButton(
                            "Start Analysis",
                            icon=ft.Icons.ANALYTICS_ROUNDED,
                            style=ft.ButtonStyle(
                                bgcolor=theme.PRIMARY,
                                color=ft.Colors.WHITE,
                                shape=ft.RoundedRectangleBorder(
                                    radius=tokens.RADIUS_MD
                                ),
                                padding=tokens.SPACE_LG,
                            ),
                            on_click=on_start_analysis,
                        ),
                    ],
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=tokens.SPACE_SM,
                ),
                padding=tokens.SPACE_XL,
                alignment=ft.Alignment.CENTER,
            )
        )
    else:
        for report in user_reports:
            reports_list_controls.append(
                ft.Container(
                    content=build_report_card(report, on_open_report),
                    margin=ft.Margin(
                        tokens.SPACE_XL,
                        tokens.SPACE_XS,
                        tokens.SPACE_XL,
                        tokens.SPACE_XS,
                    ),
                )
            )

    controls.append(ft.Column(controls=reports_list_controls))
    controls.append(_ad())
    controls.append(ft.Container(height=tokens.INPUT_WIDTH_SM))

    return ft.Column(controls=controls, scroll=ft.ScrollMode.AUTO, expand=True)
