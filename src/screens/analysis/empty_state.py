"""Empty state landing view for Analysis screen when no cells or dataset are loaded."""

from __future__ import annotations

import flet as ft

from core import theme, tokens


def build_empty_state(
    on_import,
    on_autopilot,
    has_schema: bool,
) -> ft.Container:
    """Centered landing call-to-action view."""
    return ft.Container(
        content=ft.Column(
            controls=[
                ft.Icon(
                    ft.Icons.AUTO_AWESOME_ROUNDED,
                    size=tokens.ICON_XXL,
                    color=ft.Colors.with_opacity(tokens.OPACITY_DIM, theme.PRIMARY),
                ),
                ft.Text(
                    "Ready to analyze",
                    size=tokens.FONT_LG,
                    weight=ft.FontWeight.W_600,
                    text_align=ft.TextAlign.CENTER,
                ),
                ft.Text(
                    "Import a data file or type a question above.\n"
                    "AI will write and execute code for you.",
                    size=tokens.FONT_SM,
                    color=ft.Colors.ON_SURFACE_VARIANT,
                    text_align=ft.TextAlign.CENTER,
                ),
                ft.Container(height=tokens.SPACE_MD),
                ft.Row(
                    controls=[
                        ft.OutlinedButton(
                            "Import File",
                            icon=ft.Icons.UPLOAD_FILE_ROUNDED,
                            on_click=on_import,
                        ),
                        ft.OutlinedButton(
                            "Autopilot",
                            icon=ft.Icons.ROCKET_LAUNCH_ROUNDED,
                            on_click=on_autopilot,
                            disabled=not has_schema,
                        ),
                    ],
                    alignment=ft.MainAxisAlignment.CENTER,
                    spacing=tokens.SPACE_MD,
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
