"""Dataset inspector bottom sheet modal component.

Displays dataset schema, shape, column data types, missing value counts,
summary statistics, and sample preview rows.
"""

from __future__ import annotations

import flet as ft

from core import theme, tokens


def show_dataset_inspector(
    page: ft.Page, dataset_name: str, schema: dict, on_load_in_analysis=None
):
    """Opens a bottom sheet or dialog showing dataset metadata and statistical overview."""
    if not page:
        return

    columns = schema.get("columns", [])
    dtypes = schema.get("dtypes", {})
    shape = schema.get("shape", [0, 0])
    summary_stats = schema.get("summary", {})

    rows_count = shape[0] if len(shape) > 0 else 0
    cols_count = shape[1] if len(shape) > 1 else len(columns)

    def _close(_=None):
        dlg.open = False
        page.update()

    # ── Metric cards ─────────────────────────────────────────────
    metric_shape = ft.Container(
        content=ft.Column(
            [
                ft.Text(
                    "Dataset Shape",
                    size=tokens.FONT_XS,
                    color=ft.Colors.ON_SURFACE_VARIANT,
                ),
                ft.Text(
                    f"{rows_count:,} rows × {cols_count} cols",
                    size=tokens.FONT_MD,
                    weight=ft.FontWeight.W_700,
                ),
            ],
            spacing=2,
        ),
        padding=tokens.SPACE_SM,
        border_radius=tokens.RADIUS_MD,
        bgcolor=theme.GLASS_BG,
        border=ft.Border.all(1, theme.GLASS_BORDER_COLOR),
        expand=True,
    )

    # ── Column list ──────────────────────────────────────────────
    col_tiles = []
    for col in columns:
        dtype = dtypes.get(col, "object")
        stats = summary_stats.get(col, {})
        stat_text = ""
        if stats:
            parts = []
            # Columns with all-NaN / non-numeric data serialize their
            # stats as null - formatting those crashes the inspector.
            if isinstance(stats.get("mean"), (int, float)):
                parts.append(f"mean: {stats['mean']:.2f}")
            if isinstance(stats.get("min"), (int, float)) and isinstance(
                stats.get("max"), (int, float)
            ):
                parts.append(f"range: [{stats['min']}, {stats['max']}]")
            stat_text = " · ".join(parts)

        col_tiles.append(
            ft.Container(
                content=ft.Row(
                    [
                        ft.Column(
                            [
                                ft.Text(
                                    col, size=tokens.FONT_SM, weight=ft.FontWeight.W_600
                                ),
                                ft.Text(
                                    stat_text,
                                    size=tokens.FONT_XXS,
                                    color=ft.Colors.ON_SURFACE_VARIANT,
                                )
                                if stat_text
                                else ft.Container(),
                            ],
                            spacing=2,
                            expand=True,
                        ),
                        ft.Container(
                            content=ft.Text(
                                str(dtype),
                                size=tokens.FONT_XXS,
                                weight=ft.FontWeight.W_600,
                                color=theme.PRIMARY,
                            ),
                            padding=ft.Padding(6, 2, 6, 2),
                            border_radius=tokens.RADIUS_SM,
                            bgcolor=ft.Colors.with_opacity(0.1, theme.PRIMARY),
                        ),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                ),
                padding=ft.Padding(
                    tokens.SPACE_SM, tokens.SPACE_XS, tokens.SPACE_SM, tokens.SPACE_XS
                ),
                border_radius=tokens.RADIUS_SM,
                bgcolor=theme.GLASS_BG,
            )
        )

    dlg = ft.AlertDialog(
        title=ft.Row(
            [
                ft.Icon(ft.Icons.TABLE_CHART_ROUNDED, color=theme.PRIMARY, size=24),
                ft.Text(
                    dataset_name,
                    size=tokens.FONT_MD,
                    weight=ft.FontWeight.W_600,
                    expand=True,
                ),
            ],
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        content=ft.Container(
            content=ft.Column(
                [
                    metric_shape,
                    ft.Container(height=tokens.SPACE_XS),
                    ft.Text(
                        "Columns & Metadata",
                        size=tokens.FONT_SM,
                        weight=ft.FontWeight.W_600,
                    ),
                    ft.Column(
                        col_tiles,
                        scroll=ft.ScrollMode.AUTO,
                        spacing=tokens.SPACE_XXS,
                        expand=True,
                    ),
                ],
                spacing=tokens.SPACE_XS,
                expand=True,
            ),
            width=tokens.DIALOG_WIDTH_MD,
            height=tokens.DIALOG_HEIGHT_MD,
        ),
        actions=[
            ft.TextButton("Close", on_click=_close),
            ft.FilledButton(
                "Analyze in Colab",
                icon=ft.Icons.AUTO_AWESOME_ROUNDED,
                style=ft.ButtonStyle(bgcolor=theme.PRIMARY, color=ft.Colors.WHITE),
                on_click=lambda e: (
                    _close(),
                    on_load_in_analysis() if on_load_in_analysis else None,
                ),
            ),
        ],
    )
    page.show_dialog(dlg)
