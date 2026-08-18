"""Session banner and active session chip components for Analysis screen."""

from __future__ import annotations

import flet as ft

from components.session_card import hardware_badge
from core import theme, tokens


def build_session_banner(on_connect, is_connecting: bool) -> ft.Control:
    """Big splash banner prompting user to connect to Google Colab."""
    return ft.Container(
        content=ft.Column(
            controls=[
                ft.Container(
                    content=ft.Icon(
                        ft.Icons.CLOUD_OUTLINED,
                        size=tokens.ICON_HERO,
                        color=ft.Colors.ON_SURFACE_VARIANT,
                    ),
                    alignment=ft.Alignment.CENTER,
                ),
                ft.Text(
                    "Connect to Google Colab",
                    size=tokens.FONT_XL,
                    weight=ft.FontWeight.W_600,
                    text_align=ft.TextAlign.CENTER,
                ),
                ft.Text(
                    "Start a cloud VM to run your analysis.\nFree GPU (T4) included.",
                    size=tokens.FONT_SM,
                    color=ft.Colors.ON_SURFACE_VARIANT,
                    text_align=ft.TextAlign.CENTER,
                ),
                ft.Container(height=tokens.SPACE_MD),
                ft.FilledButton(
                    "Start Session",
                    icon=ft.Icons.ROCKET_LAUNCH_ROUNDED,
                    on_click=on_connect,
                    disabled=is_connecting,
                    style=ft.ButtonStyle(
                        bgcolor=theme.PRIMARY,
                        color=ft.Colors.WHITE,
                        padding=ft.Padding(
                            tokens.SPACE_XXL,
                            tokens.SPACE_MD,
                            tokens.SPACE_XXL,
                            tokens.SPACE_MD,
                        ),
                        shape=ft.RoundedRectangleBorder(radius=tokens.RADIUS_MD),
                    ),
                ),
                ft.ProgressRing(
                    visible=is_connecting,
                    width=tokens.PROGRESS_RING_LG,
                    height=tokens.PROGRESS_RING_LG,
                    stroke_width=tokens.PROGRESS_RING_STROKE_THIN,
                ),
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            alignment=ft.MainAxisAlignment.CENTER,
            spacing=tokens.SPACE_SM,
        ),
        expand=True,
        alignment=ft.Alignment.CENTER,
        padding=tokens.SPACE_XL,
    )


def build_session_chip(session_name: str, hw_label: str) -> ft.Container:
    """Pill chip displaying the active connected session and hardware accelerator."""
    hw_label = hw_label or "CPU"
    return ft.Container(
        content=ft.Row(
            controls=[
                ft.Icon(
                    ft.Icons.CLOUD_DONE_ROUNDED,
                    size=tokens.ICON_XS,
                    color=theme.SUCCESS,
                ),
                ft.Text(
                    f"{session_name}",
                    size=tokens.FONT_XS,
                    weight=ft.FontWeight.W_600,
                    color=theme.SUCCESS,
                ),
                hardware_badge(
                    "NONE" if hw_label == "CPU" else hw_label,
                    "GPU"
                    if hw_label not in ("CPU", "V5E1", "V6E1")
                    else ("TPU" if hw_label in ("V5E1", "V6E1") else "DEFAULT"),
                ),
            ],
            spacing=tokens.SPACE_XS,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        padding=ft.Padding(
            tokens.SPACE_MD, tokens.SPACE_XS, tokens.SPACE_MD, tokens.SPACE_XS
        ),
        border_radius=tokens.RADIUS_PILL,
        bgcolor=ft.Colors.with_opacity(tokens.OPACITY_SUBTLE, theme.SUCCESS),
        border=ft.Border.all(
            tokens.DIVIDER_THICKNESS,
            ft.Colors.with_opacity(tokens.OPACITY_BORDER, theme.SUCCESS),
        ),
    )
