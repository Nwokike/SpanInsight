"""AI report arranger loading screen."""

from __future__ import annotations

import flet as ft

from core import theme, tokens, utils


def build_arranger_view(page: ft.Page) -> ft.Control:
    """Loading spinner view displayed while AI organizes blocks and polishes titles."""
    controls = [
        ft.Container(height=tokens.PIE_CHART_RADIUS),
        ft.ProgressRing(
            width=tokens.ICON_CONTAINER_SIZE,
            height=tokens.ICON_CONTAINER_SIZE,
            stroke_width=tokens.PROGRESS_RING_STROKE_NORMAL,
        ),
        ft.Text(
            "AI is arranging your report...",
            size=tokens.FONT_MD,
            color=ft.Colors.ON_SURFACE_VARIANT,
        ),
        ft.Text(
            "Optimizing order, polishing descriptions",
            size=tokens.FONT_BODY_SM,
            color=ft.Colors.with_opacity(tokens.OPACITY_HALF, ft.Colors.ON_SURFACE),
        ),
    ]

    if page and page.platform in (ft.PagePlatform.ANDROID, ft.PagePlatform.IOS):
        controls.append(
            ft.Container(
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
                border=ft.Border.all(
                    tokens.DIVIDER_THICKNESS, theme.GLASS_BORDER_COLOR
                ),
                margin=ft.Margin(
                    tokens.SPACE_NONE,
                    tokens.SPACE_MD,
                    tokens.SPACE_NONE,
                    tokens.SPACE_NONE,
                ),
            )
        )

    return ft.Container(
        content=ft.Column(
            controls,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=tokens.SPACE_MD,
        ),
        expand=True,
        alignment=ft.Alignment.CENTER,
    )
