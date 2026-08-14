"""Autopilot progress bar component for Analysis screen."""

from __future__ import annotations

import flet as ft

from core import theme, tokens


def build_autopilot_bar(
    is_running: bool,
    progress_text: str,
    on_stop,
) -> ft.Container:
    """Status bar showing active multi-step autopilot progress with a stop action."""
    if not is_running:
        return ft.Container(visible=False)

    return ft.Container(
        content=ft.Row(
            controls=[
                ft.ProgressRing(width=14, height=14, stroke_width=2),
                ft.Text(
                    progress_text or "Running...",
                    size=tokens.FONT_XS,
                    weight=ft.FontWeight.W_500,
                    expand=True,
                ),
                ft.TextButton(
                    "Stop",
                    on_click=on_stop,
                    style=ft.ButtonStyle(
                        color=theme.ERROR,
                        padding=ft.Padding(8, 4, 8, 4),
                    ),
                ),
            ],
            spacing=tokens.SPACE_SM,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        padding=ft.Padding(
            tokens.SPACE_MD,
            tokens.SPACE_XS,
            tokens.SPACE_MD,
            tokens.SPACE_XS,
        ),
        bgcolor=ft.Colors.with_opacity(0.06, theme.ACCENT),
        border=ft.Border.all(1, ft.Colors.with_opacity(0.15, theme.ACCENT)),
        border_radius=tokens.RADIUS_SM,
        margin=ft.Margin(tokens.SPACE_MD, 0, tokens.SPACE_MD, tokens.SPACE_XS),
    )
