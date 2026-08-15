"""File import card — Modern dashed upload area with FilePicker integration."""

from __future__ import annotations

from collections.abc import Callable

import flet as ft

from core import theme, tokens


def build_file_import_card(
    on_pick: Callable[[], None],
    is_loading: bool = False,
    loading_message: str = "Loading dataset...",
) -> ft.Container:
    """Build the file import upload area supporting broad data formats on Colab VM."""
    if is_loading:
        content = ft.Column(
            controls=[
                ft.ProgressRing(width=36, height=36, stroke_width=3),
                ft.Text(
                    loading_message,
                    size=tokens.FONT_MD,
                    color=ft.Colors.ON_SURFACE_VARIANT,
                ),
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=tokens.SPACE_LG,
        )
    else:
        format_pills = [
            ".csv",
            ".xlsx",
            ".parquet",
            ".json",
            ".tsv",
            ".dta",
            ".sav",
            ".sas7bdat",
            ".sqlite",
            ".h5",
            ".npy",
            ".zip",
        ]

        content = ft.Column(
            controls=[
                ft.Container(
                    content=ft.Icon(
                        ft.Icons.UPLOAD_FILE_ROUNDED,
                        size=tokens.ICON_XXL,
                        color=theme.PRIMARY_LIGHT,
                    ),
                    width=72,
                    height=72,
                    border_radius=tokens.RADIUS_XXL,
                    bgcolor=ft.Colors.with_opacity(0.08, theme.PRIMARY),
                    alignment=ft.Alignment.CENTER,
                ),
                ft.Text(
                    "Import Dataset",
                    size=tokens.FONT_LG,
                    weight=ft.FontWeight.W_600,
                ),
                ft.Text(
                    "Tap to select any dataset or scientific data file",
                    size=tokens.FONT_SM,
                    color=ft.Colors.ON_SURFACE_VARIANT,
                ),
                ft.Container(height=tokens.SPACE_XS),
                ft.Row(
                    controls=[
                        ft.Container(
                            content=ft.Text(
                                ext,
                                size=tokens.FONT_XXS,
                                color=theme.ACCENT,
                                weight=ft.FontWeight.W_500,
                            ),
                            padding=ft.Padding(
                                left=tokens.SPACE_SM,
                                right=tokens.SPACE_SM,
                                top=tokens.SPACE_XXS,
                                bottom=tokens.SPACE_XXS,
                            ),
                            border_radius=tokens.RADIUS_SM,
                            bgcolor=ft.Colors.with_opacity(0.1, theme.ACCENT),
                        )
                        for ext in format_pills
                    ],
                    alignment=ft.MainAxisAlignment.CENTER,
                    spacing=tokens.SPACE_XS,
                    wrap=True,
                ),
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=tokens.SPACE_SM,
        )

    return ft.Container(
        content=content,
        padding=tokens.SPACE_XXL,
        border_radius=tokens.RADIUS_XL,
        border=ft.Border.all(
            2,
            ft.Colors.with_opacity(0.25, theme.PRIMARY),
        ),
        bgcolor=ft.Colors.with_opacity(0.03, ft.Colors.WHITE),
        alignment=ft.Alignment.CENTER,
        on_click=lambda _: on_pick() if not is_loading else None,
        ink=not is_loading,
        animate=ft.Animation(tokens.ANIM_DEFAULT_MS, ft.AnimationCurve.EASE_OUT),
        margin=ft.Margin(
            tokens.SPACE_MD, tokens.SPACE_MD, tokens.SPACE_MD, tokens.SPACE_MD
        ),
    )
