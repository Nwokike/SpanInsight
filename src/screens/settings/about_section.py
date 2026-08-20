"""About, terms, privacy, and pro tease section for Settings."""

from __future__ import annotations

import flet as ft

from core import theme, tokens
from core.constants import APP_VERSION
from core.styles import glass_card, section_header


def build_about_section(
    cli_version: str,
    on_launch_privacy,
    on_launch_terms,
) -> list[ft.Control]:
    """App metadata, version info, terms links, and SpanInsight Pro card."""
    return [
        section_header("About"),
        glass_card(
            ft.Column(
                controls=[
                    ft.Container(
                        content=ft.Image(
                            src="icon.png",
                            width=tokens.AVATAR_CONTAINER_SIZE,
                            height=tokens.AVATAR_CONTAINER_SIZE,
                            fit=ft.BoxFit.CONTAIN,
                        ),
                        alignment=ft.Alignment.CENTER,
                        margin=ft.Margin(
                            tokens.SPACE_NONE,
                            tokens.SPACE_NONE,
                            tokens.SPACE_NONE,
                            tokens.SPACE_SM,
                        ),
                    ),
                    ft.Text(
                        "Autonomous Data Intelligence for Everyone",
                        size=tokens.FONT_SM,
                        color=ft.Colors.ON_SURFACE_VARIANT,
                        text_align=ft.TextAlign.CENTER,
                    ),
                    ft.Container(height=tokens.SPACE_SM),
                    ft.Row(
                        [
                            ft.Text("Version", size=tokens.FONT_SM),
                            ft.Text(
                                f"v{APP_VERSION}",
                                size=tokens.FONT_SM,
                                color=ft.Colors.ON_SURFACE_VARIANT,
                            ),
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    ),
                    ft.Row(
                        [
                            ft.Text("Powered by", size=tokens.FONT_SM),
                            ft.Text(
                                f"Google Colab (CLI v{cli_version})",
                                size=tokens.FONT_SM,
                                color=ft.Colors.ON_SURFACE_VARIANT,
                            ),
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    ),
                    ft.Divider(
                        height=tokens.DIVIDER_THICKNESS,
                        color=ft.Colors.with_opacity(
                            tokens.OPACITY_SUBTLE, ft.Colors.ON_SURFACE
                        ),
                    ),
                    ft.Row(
                        [
                            ft.TextButton(
                                "Privacy Policy",
                                icon=ft.Icons.PRIVACY_TIP_ROUNDED,
                                style=ft.ButtonStyle(color=theme.PRIMARY),
                                on_click=on_launch_privacy,
                            ),
                            ft.TextButton(
                                "Terms of Service",
                                icon=ft.Icons.GAVEL_ROUNDED,
                                style=ft.ButtonStyle(color=theme.PRIMARY),
                                on_click=on_launch_terms,
                            ),
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_EVENLY,
                    ),
                ],
                spacing=tokens.SPACE_XS,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            ),
        ),
        # Pro tease
        ft.Container(
            content=ft.Row(
                controls=[
                    ft.Icon(
                        ft.Icons.WORKSPACE_PREMIUM_ROUNDED,
                        size=tokens.ICON_LG,
                        color=ft.Colors.with_opacity(
                            tokens.OPACITY_DISABLED, theme.PRIMARY
                        ),
                    ),
                    ft.Column(
                        [
                            ft.Text(
                                "SpanInsight Pro",
                                size=tokens.FONT_MD,
                                weight=ft.FontWeight.W_500,
                                color=ft.Colors.with_opacity(
                                    tokens.OPACITY_HALF, ft.Colors.ON_SURFACE
                                ),
                            ),
                            ft.Text(
                                "Zero ads • Unlimited credits • Priority support",
                                size=tokens.FONT_XS,
                                color=ft.Colors.with_opacity(
                                    tokens.OPACITY_DIM, ft.Colors.ON_SURFACE
                                ),
                            ),
                        ],
                        spacing=tokens.SPACE_XXS,
                        expand=True,
                    ),
                    ft.Container(
                        content=ft.Text(
                            "SOON",
                            size=tokens.FONT_XXS,
                            weight=ft.FontWeight.W_700,
                            color=theme.ACCENT,
                        ),
                        padding=ft.Padding(
                            tokens.SPACE_SM,
                            tokens.SPACE_XXS,
                            tokens.SPACE_SM,
                            tokens.SPACE_XXS,
                        ),
                        border_radius=tokens.RADIUS_SM,
                        bgcolor=ft.Colors.with_opacity(
                            tokens.OPACITY_LIGHT, theme.ACCENT
                        ),
                    ),
                ],
                spacing=tokens.SPACE_LG,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            padding=ft.Padding(
                tokens.SPACE_LG,
                tokens.BUTTON_PADDING_MD,
                tokens.SPACE_LG,
                tokens.BUTTON_PADDING_MD,
            ),
            opacity=tokens.OPACITY_MUTED_BORDER,
        ),
    ]
