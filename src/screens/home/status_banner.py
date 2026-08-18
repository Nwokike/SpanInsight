"""Colab status bar component for HomeScreen."""

from __future__ import annotations

import flet as ft

from core import theme, tokens


def build_colab_status_bar(state) -> ft.Container:
    """Status bar showing Colab connected or offline network state."""
    if state.colab_connected:
        return ft.Container(
            content=ft.Row(
                controls=[
                    ft.Icon(
                        ft.Icons.CLOUD_DONE_ROUNDED,
                        size=tokens.ICON_XS,
                        color=theme.SUCCESS,
                    ),
                    ft.Text(
                        f"Colab connected — {state.session_hardware}",
                        size=tokens.FONT_XS,
                        color=theme.SUCCESS,
                        weight=ft.FontWeight.W_600,
                    ),
                ],
                spacing=tokens.SPACE_SM,
                alignment=ft.MainAxisAlignment.CENTER,
            ),
            padding=ft.Padding(
                tokens.SPACE_NONE,
                tokens.SPACE_SM,
                tokens.SPACE_NONE,
                tokens.SPACE_SM,
            ),
            bgcolor=ft.Colors.with_opacity(tokens.OPACITY_SUBTLE, theme.SUCCESS),
            border=ft.Border(
                bottom=ft.BorderSide(
                    tokens.DIVIDER_THICKNESS,
                    ft.Colors.with_opacity(tokens.OPACITY_BORDER, theme.SUCCESS),
                )
            ),
        )
    elif not state.gateway_online:
        return ft.Container(
            content=ft.Row(
                controls=[
                    ft.Icon(
                        ft.Icons.WIFI_OFF_ROUNDED,
                        size=tokens.ICON_XS,
                        color=theme.WARNING,
                    ),
                    ft.Text(
                        "No internet connection",
                        size=tokens.FONT_XS,
                        weight=ft.FontWeight.W_500,
                        color=theme.WARNING,
                    ),
                ],
                spacing=tokens.SPACE_SM,
                alignment=ft.MainAxisAlignment.CENTER,
            ),
            padding=ft.Padding(
                tokens.SPACE_NONE,
                tokens.SPACE_SM,
                tokens.SPACE_NONE,
                tokens.SPACE_SM,
            ),
            bgcolor=ft.Colors.with_opacity(tokens.OPACITY_MUTED, theme.WARNING),
            border=ft.Border(
                bottom=ft.BorderSide(
                    tokens.DIVIDER_THICKNESS,
                    ft.Colors.with_opacity(tokens.OPACITY_BORDER, theme.WARNING),
                )
            ),
        )
    return ft.Container()
