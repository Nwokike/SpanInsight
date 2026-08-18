"""Reusable branding header component containing the official logo and consistent tagline."""

from __future__ import annotations

import flet as ft

from core import tokens


def build_brand_header(
    show_tagline: bool = True, spacing_below: bool = True
) -> ft.Container:
    """Build the unified brand header containing the logo image and tagline."""
    controls = [
        ft.Container(height=tokens.SPACE_LG),
        ft.Image(
            src="logo.png",
            width=tokens.BRAND_LOGO_WIDTH,
            height=tokens.BRAND_LOGO_HEIGHT,
            fit=ft.BoxFit.CONTAIN,
        ),
    ]

    if show_tagline:
        controls.extend(
            [
                ft.Container(height=tokens.SPACE_SM),
                ft.Text(
                    "Autonomous Data Intelligence for Everyone",
                    size=tokens.FONT_SM,
                    color=ft.Colors.ON_SURFACE_VARIANT,
                    text_align=ft.TextAlign.CENTER,
                ),
            ]
        )

    if spacing_below:
        controls.append(ft.Container(height=tokens.SPACE_XL))

    return ft.Container(
        content=ft.Column(
            controls=controls,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=tokens.SPACE_NONE,
        ),
    )
