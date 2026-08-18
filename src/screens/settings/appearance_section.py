"""Theme and appearance settings section."""

from __future__ import annotations

from collections.abc import Callable

import flet as ft

from core import theme, tokens
from core.styles import section_header


def build_appearance_section(
    current_theme: str,
    on_theme_changed: Callable[[str], None],
) -> list[ft.Control]:
    """Light / Dark / System 3-card theme selector matching DDGS pattern."""

    def create_theme_card(mode: str, label: str, icon: str) -> ft.Container:
        is_sel = current_theme == mode
        return ft.Container(
            content=ft.Row(
                [
                    ft.Icon(
                        icon,
                        color=theme.PRIMARY if is_sel else ft.Colors.ON_SURFACE_VARIANT,
                        size=tokens.ICON_MD,
                    ),
                    ft.Text(
                        label,
                        size=tokens.FONT_SM,
                        weight=ft.FontWeight.W_600 if is_sel else ft.FontWeight.NORMAL,
                        color=theme.PRIMARY if is_sel else ft.Colors.ON_SURFACE,
                    ),
                ],
                alignment=ft.MainAxisAlignment.CENTER,
                spacing=tokens.SPACE_SM_XS,
            ),
            padding=ft.Padding(
                tokens.SPACE_MD_SM,
                tokens.SPACE_MD_SM,
                tokens.SPACE_MD_SM,
                tokens.SPACE_MD_SM,
            ),
            border_radius=tokens.RADIUS_MD,
            border=ft.Border.all(tokens.DIVIDER_THICKNESS_THICK, theme.PRIMARY)
            if is_sel
            else ft.Border.all(
                tokens.DIVIDER_THICKNESS,
                ft.Colors.with_opacity(tokens.OPACITY_CONTAINER, ft.Colors.ON_SURFACE),
            ),
            bgcolor=ft.Colors.with_opacity(tokens.OPACITY_LIGHT, theme.PRIMARY)
            if is_sel
            else ft.Colors.SURFACE_CONTAINER_HIGHEST,
            expand=True,
            animate=ft.Animation(tokens.ANIMATION_MS_FAST, ft.AnimationCurve.EASE_OUT),
            on_click=lambda e: on_theme_changed(mode),
        )

    light_btn = create_theme_card("light", "Light", ft.Icons.LIGHT_MODE_ROUNDED)
    dark_btn = create_theme_card("dark", "Dark", ft.Icons.DARK_MODE_ROUNDED)
    system_btn = create_theme_card("system", "System", ft.Icons.BRIGHTNESS_AUTO_ROUNDED)

    return [
        section_header("Appearance"),
        ft.Container(
            content=ft.Row(
                controls=[light_btn, dark_btn, system_btn],
                spacing=tokens.SPACE_SM,
            ),
            padding=ft.Padding(
                tokens.SPACE_LG,
                tokens.SPACE_SM_XS,
                tokens.SPACE_LG,
                tokens.BUTTON_PADDING_MD,
            ),
        ),
    ]
