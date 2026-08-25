"""OfflineFlow — retry-only no-internet surface shown in place of onboarding.

Ported from collabshell's OfflineFlow pattern (KTV Player lineage): pure
presentational function taking an `on_retry` callback; the parent owns the
probing logic. Rendered INSTEAD of the onboarding slides when the device is
offline, so a Colab-built app never traps users mid-signup.
"""

from __future__ import annotations

import flet as ft
from flet import Control

from core import theme, tokens


def OfflineFlow(on_retry) -> Control:
    """Centered offline card with a single Retry Connection button."""
    return ft.Container(
        alignment=ft.Alignment(0.0, 0.0),
        expand=True,
        padding=ft.Padding(tokens.SPACE_LG, 0, tokens.SPACE_LG, 0),
        content=ft.Column(
            controls=[
                ft.Icon(
                    ft.Icons.CLOUD_OFF_ROUNDED,
                    size=tokens.ICON_XXL,
                    color=theme.WARNING,
                ),
                ft.Container(height=tokens.SPACE_MD),
                ft.Text(
                    "No internet connection",
                    size=tokens.FONT_XL,
                    weight=ft.FontWeight.W_700,
                    text_align=ft.TextAlign.CENTER,
                ),
                ft.Container(height=tokens.SPACE_SM),
                ft.Text(
                    "Check your network and try again.\n"
                    "You need a connection to sign in and manage sessions.",
                    size=tokens.FONT_SM,
                    color=ft.Colors.ON_SURFACE_VARIANT,
                    text_align=ft.TextAlign.CENTER,
                ),
                ft.Container(height=tokens.SPACE_XL),
                ft.FilledButton(
                    content=ft.Text("Retry Connection"),
                    icon=ft.Icons.REFRESH_ROUNDED,
                    on_click=on_retry,
                ),
            ],
            alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=0,
        ),
    )
