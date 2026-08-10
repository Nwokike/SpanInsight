"""Chart card — individual chart + insight for the report view."""

from __future__ import annotations

import base64

import flet as ft

from core import theme, tokens


def build_chart_card(
    index: int,
    prompt: str,
    figure=None,
    insight: str = "",
    code: str = "",
    on_change: callable | None = None,
) -> ft.Container:
    """Build a single chart card with its AI insight."""
    chart_widget = ft.Container(height=10)  # fallback

    if figure:
        b64_img = ""
        # Handle raw bytes from Sandbox backend
        if isinstance(figure, bytes):
            b64_img = base64.b64encode(figure).decode("utf-8")
        # Handle string if it's already encoded by ReportService
        elif isinstance(figure, str):
            b64_img = figure

        if b64_img:
            chart_widget = ft.Container(
                content=ft.Image(
                    src=b64_img,
                    fit="contain",
                ),
                height=280,
                border_radius=tokens.RADIUS_MD,
                clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
                alignment=ft.Alignment.CENTER,
            )

    return ft.Container(
        content=ft.Column(
            controls=[
                # Header
                ft.Row(
                    controls=[
                        ft.Container(
                            content=ft.Text(
                                str(index),
                                size=tokens.FONT_SM,
                                weight=ft.FontWeight.W_700,
                                color=ft.Colors.WHITE,
                                text_align=ft.TextAlign.CENTER,
                            ),
                            width=28,
                            height=28,
                            border_radius=14,
                            bgcolor=theme.PRIMARY,
                            alignment=ft.Alignment.CENTER,
                        ),
                        ft.Text(
                            prompt,
                            size=tokens.FONT_SM,
                            weight=ft.FontWeight.W_600,
                            max_lines=2,
                            overflow=ft.TextOverflow.ELLIPSIS,
                            expand=True,
                        ),
                    ],
                    spacing=tokens.SPACE_MD,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                # Chart
                chart_widget,
                # Insight
                ft.Container(
                    content=ft.Row(
                        controls=[
                            ft.Icon(
                                ft.Icons.LIGHTBULB_OUTLINE_ROUNDED,
                                size=tokens.ICON_SM,
                                color=theme.ACCENT,
                            ),
                            ft.TextField(
                                value=insight or "",
                                multiline=True,
                                border=ft.InputBorder.NONE,
                                content_padding=0,
                                text_size=13,
                                expand=True,
                                on_change=on_change,
                            ),
                        ],
                        spacing=tokens.SPACE_SM,
                        vertical_alignment=ft.CrossAxisAlignment.START,
                    ),
                    padding=ft.Padding(
                        left=tokens.SPACE_MD,
                        right=tokens.SPACE_MD,
                        top=tokens.SPACE_MD,
                        bottom=tokens.SPACE_MD,
                    ),
                    border_radius=tokens.RADIUS_MD,
                    bgcolor=ft.Colors.with_opacity(0.04, theme.ACCENT),
                ),
            ],
            spacing=tokens.SPACE_MD,
        ),
        padding=tokens.SPACE_LG,
        border_radius=tokens.RADIUS_XL,
        bgcolor=theme.GLASS_BG,
        border=ft.Border.all(1, theme.GLASS_BORDER_COLOR),
    )
