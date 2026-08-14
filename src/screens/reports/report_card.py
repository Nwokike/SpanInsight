"""Report card item component for Reports dashboard."""

from __future__ import annotations

from datetime import UTC, datetime

import flet as ft

from core import theme


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
        on_click=lambda e: on_open(report),
        ink=True,
    )
