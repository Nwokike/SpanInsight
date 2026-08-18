"""Hardware accelerators and execution defaults section for Settings."""

from __future__ import annotations

import flet as ft

from core import tokens
from core.constants import ACCELERATOR_OPTIONS, TIMEOUT_OPTIONS
from core.styles import glass_card, section_header


def build_hardware_section(
    state,
    on_accelerator_change,
    on_timeout_change,
    on_keep_alive_change,
) -> list[ft.Control]:
    """Default runtime accelerator options and execution timeout switches."""
    current_acc = state.default_tpu or state.default_gpu or ""

    return [
        section_header("Hardware & Runtime"),
        glass_card(
            ft.Column(
                controls=[
                    ft.Row(
                        controls=[
                            ft.Icon(
                                ft.Icons.DEVELOPER_BOARD_ROUNDED,
                                size=tokens.ICON_LG,
                                color=ft.Colors.ON_SURFACE_VARIANT,
                            ),
                            ft.Column(
                                [
                                    ft.Text(
                                        "Default Accelerator",
                                        size=tokens.FONT_MD,
                                        weight=ft.FontWeight.W_500,
                                    ),
                                    ft.Text(
                                        "Pre-selected runtime (auto-fallbacks to CPU if quota limited)",
                                        size=tokens.FONT_XS,
                                        color=ft.Colors.ON_SURFACE_VARIANT,
                                        italic=True,
                                    ),
                                ],
                                spacing=tokens.SPACE_XXS,
                                expand=True,
                            ),
                            ft.Dropdown(
                                value=current_acc,
                                options=[
                                    ft.dropdown.Option(k, v)
                                    for k, v in ACCELERATOR_OPTIONS
                                ],
                                width=tokens.DROPDOWN_WIDTH_LG,
                                border_radius=tokens.RADIUS_MD,
                                text_size=tokens.FONT_SM,
                                on_select=on_accelerator_change,
                            ),
                        ],
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=tokens.SPACE_LG,
                    ),
                ],
            ),
        ),
        section_header("Execution & Reliability"),
        glass_card(
            ft.Column(
                controls=[
                    ft.Row(
                        controls=[
                            ft.Icon(
                                ft.Icons.TIMER_ROUNDED,
                                size=tokens.ICON_LG,
                                color=ft.Colors.ON_SURFACE_VARIANT,
                            ),
                            ft.Column(
                                [
                                    ft.Text(
                                        "Default Timeout",
                                        size=tokens.FONT_MD,
                                        weight=ft.FontWeight.W_500,
                                    ),
                                    ft.Text(
                                        "Max wait for code execution",
                                        size=tokens.FONT_XS,
                                        color=ft.Colors.ON_SURFACE_VARIANT,
                                        italic=True,
                                    ),
                                ],
                                spacing=tokens.SPACE_XXS,
                                expand=True,
                            ),
                            ft.Dropdown(
                                value=str(state.default_timeout),
                                options=[
                                    ft.dropdown.Option(str(t), f"{t}s")
                                    for t in TIMEOUT_OPTIONS
                                ],
                                width=tokens.DROPDOWN_WIDTH_SM,
                                border_radius=tokens.RADIUS_MD,
                                text_size=tokens.FONT_SM,
                                on_select=on_timeout_change,
                            ),
                        ],
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=tokens.SPACE_LG,
                    ),
                    ft.Divider(height=tokens.SPACE_SM),
                    ft.Row(
                        controls=[
                            ft.Icon(
                                ft.Icons.BOLT_ROUNDED,
                                size=tokens.ICON_LG,
                                color=ft.Colors.ON_SURFACE_VARIANT,
                            ),
                            ft.Column(
                                [
                                    ft.Text(
                                        "Keep-Alive Session",
                                        size=tokens.FONT_MD,
                                        weight=ft.FontWeight.W_500,
                                    ),
                                    ft.Text(
                                        "Prevent Colab VM from idling out during analysis",
                                        size=tokens.FONT_XS,
                                        color=ft.Colors.ON_SURFACE_VARIANT,
                                        italic=True,
                                    ),
                                ],
                                spacing=tokens.SPACE_XXS,
                                expand=True,
                            ),
                            ft.Switch(
                                value=state.keep_alive_enabled,
                                on_change=on_keep_alive_change,
                            ),
                        ],
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                ],
            ),
        ),
    ]
