"""AI report arranger loading screen."""

from __future__ import annotations

import flet as ft

from core import theme, utils


def build_arranger_view(page: ft.Page) -> ft.Control:
    """Loading spinner view displayed while AI organizes blocks and polishes titles."""
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

    if page and page.platform in (ft.PagePlatform.ANDROID, ft.PagePlatform.IOS):
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
                margin=ft.Margin(0, 12, 0, 0),
            )
        )

    return ft.Container(
        content=ft.Column(controls, horizontal_alignment="center", spacing=12),
        expand=True,
        alignment=ft.Alignment.CENTER,
    )
