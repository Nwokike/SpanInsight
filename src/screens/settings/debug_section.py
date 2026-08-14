"""Debug terminal section for running diagnostics on active Colab VM."""

from __future__ import annotations

import flet as ft

from core import tokens
from core.styles import glass_card, section_header


def build_debug_section(
    terminal_output: str,
    terminal_visible: bool,
    on_run_debug,
) -> list[ft.Control]:
    """Debug section with Play button and monospace output container."""
    return [
        section_header("Debug"),
        glass_card(
            ft.Column(
                controls=[
                    ft.Row(
                        controls=[
                            ft.Icon(
                                ft.Icons.TERMINAL_ROUNDED,
                                size=tokens.ICON_LG,
                                color=ft.Colors.ON_SURFACE_VARIANT,
                            ),
                            ft.Column(
                                [
                                    ft.Text(
                                        "Debug Terminal",
                                        size=tokens.FONT_MD,
                                        weight=ft.FontWeight.W_500,
                                    ),
                                    ft.Text(
                                        "Run diagnostics on the active Colab session",
                                        size=tokens.FONT_XS,
                                        color=ft.Colors.ON_SURFACE_VARIANT,
                                        italic=True,
                                    ),
                                ],
                                spacing=tokens.SPACE_XXS,
                                expand=True,
                            ),
                            ft.FilledTonalButton(
                                content=ft.Text("Run"),
                                icon=ft.Icons.PLAY_ARROW_ROUNDED,
                                on_click=on_run_debug,
                            ),
                        ],
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=tokens.SPACE_LG,
                    ),
                    ft.Text(
                        value=terminal_output,
                        size=tokens.FONT_XS,
                        color=ft.Colors.ON_SURFACE_VARIANT,
                        selectable=True,
                        visible=terminal_visible,
                        font_family="monospace",
                    ),
                ],
            ),
        ),
    ]
