"""Report card item component for Reports dashboard."""

from __future__ import annotations

from datetime import UTC, datetime

import flet as ft

from core import theme, tokens


def build_report_card(report: dict, on_open) -> ft.Container:
    """Card item showing report title, block count, dataset name, creation date, and share badge."""
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
                        size=tokens.ICON_LG,
                    ),
                    width=tokens.BUTTON_HEIGHT_LG,
                    height=tokens.BUTTON_HEIGHT_LG,
                    border_radius=tokens.RADIUS_MD,
                    bgcolor=ft.Colors.with_opacity(tokens.OPACITY_LIGHT, theme.PRIMARY),
                    alignment=ft.Alignment.CENTER,
                ),
                ft.Column(
                    [
                        ft.Text(
                            report.get("title", "Untitled Report"),
                            weight=ft.FontWeight.W_600,
                            size=tokens.FONT_MD,
                            max_lines=1,
                            overflow=ft.TextOverflow.ELLIPSIS,
                        ),
                        ft.Text(
                            f"{block_count} block{'s' if block_count != 1 else ''} · {report.get('dataset_name', '')} · {time_str}",
                            size=tokens.FONT_SM,
                            color=ft.Colors.ON_SURFACE_VARIANT,
                            max_lines=1,
                        ),
                    ],
                    spacing=tokens.SPACE_XXS,
                    expand=True,
                ),
                ft.Row(
                    [
                        ft.Container(
                            content=ft.Text(
                                "Shared" if report.get("share_url") else "",
                                size=tokens.FONT_XS,
                                color=theme.SUCCESS,
                            ),
                            visible=bool(report.get("share_url")),
                        ),
                        ft.Icon(
                            ft.Icons.CHEVRON_RIGHT_ROUNDED,
                            color=ft.Colors.ON_SURFACE_VARIANT,
                        ),
                    ],
                    spacing=tokens.SPACE_XS,
                ),
            ],
            spacing=tokens.SPACE_MD,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        padding=tokens.BUTTON_PADDING_MD,
        border_radius=tokens.RADIUS_MD_LG,
        bgcolor=theme.GLASS_BG,
        border=ft.Border.all(tokens.DIVIDER_THICKNESS, theme.GLASS_BORDER_COLOR),
        on_click=lambda e: on_open(report),
        ink=True,
    )
