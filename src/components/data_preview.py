"""Data preview component — shows a scrollable table preview of a DataFrame."""

import flet as ft

from core import theme, tokens
from core.styles import glass_card


def build_data_preview(df) -> ft.Container:
    """Build a data table preview of the first 50 rows of a DataFrame."""
    if df is None:
        return ft.Container()

    if len(df) == 0:
        return glass_card(
            ft.Text(
                "Dataset is empty (0 rows)",
                size=tokens.FONT_SM,
                color=ft.Colors.ON_SURFACE_VARIANT,
                text_align=ft.TextAlign.CENTER,
            )
        )

    max_rows = 50
    max_cell_len = 40
    preview_df = df.head(max_rows)

    def _truncate(val) -> str:
        s = str(val) if val is not None else ""
        return s[:max_cell_len] + "…" if len(s) > max_cell_len else s

    columns = [
        ft.DataColumn(
            ft.Text(
                _truncate(col),
                size=tokens.FONT_XS,
                weight=ft.FontWeight.W_600,
            )
        )
        for col in preview_df.columns
    ]

    rows = []
    for i, (_, row) in enumerate(preview_df.iterrows()):
        rows.append(
            ft.DataRow(
                cells=[
                    ft.DataCell(ft.Text(_truncate(row[col]), size=tokens.FONT_XS))
                    for col in preview_df.columns
                ],
                color=ft.Colors.with_opacity(0.02, ft.Colors.ON_SURFACE)
                if i % 2 == 0
                else None,
            )
        )

    row_label = f"{len(df):,} rows" if len(df) > max_rows else f"{len(df)} rows"

    return glass_card(
        ft.Column(
            [
                ft.Row(
                    [
                        ft.Icon(
                            ft.Icons.TABLE_CHART_ROUNDED, size=16, color=theme.PRIMARY
                        ),
                        ft.Text(
                            f"Preview (first {min(len(df), max_rows)} of {row_label})",
                            size=tokens.FONT_SM,
                            weight=ft.FontWeight.W_600,
                        ),
                    ],
                    spacing=tokens.SPACE_SM,
                ),
                ft.Container(
                    content=ft.DataTable(
                        columns=columns,
                        rows=rows,
                        column_spacing=20,
                        horizontal_lines=ft.BorderSide(
                            0.5, ft.Colors.with_opacity(0.08, ft.Colors.ON_SURFACE)
                        ),
                        heading_row_height=36,
                        data_row_min_height=30,
                        data_row_max_height=30,
                    ),
                    border_radius=tokens.RADIUS_SM,
                    clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
                ),
            ],
            spacing=tokens.SPACE_SM,
            scroll=ft.ScrollMode.AUTO,
        )
    )
