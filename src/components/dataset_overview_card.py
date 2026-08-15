"""DatasetOverviewCard — SpanInsight's rich initial dataset overview component.

Renders dataset shape, memory footprint, column type chips, statistical summary
table (df.describe()), and initial AI starter suggestions.
"""

from __future__ import annotations

import logging
from collections.abc import Callable

import flet as ft

from core import theme, tokens

logger = logging.getLogger("DatasetOverviewCard")


def build_dataset_overview_card(
    dataset_name: str,
    schema: dict,
    page: ft.Page,
    initial_description: str = "",
    suggestions: list[str] | None = None,
    on_suggestion_selected: Callable[[str], None] | None = None,
    on_view_raw_data: Callable[[], None] | None = None,
) -> ft.Container:
    """Build a rich glassmorphic Dataset Overview Card."""
    columns = schema.get("columns", [])
    dtypes = schema.get("dtypes", {})
    shape = schema.get("shape", [0, 0])
    summary_stats = schema.get("summary", {})

    rows_count = shape[0] if len(shape) > 0 else 0
    cols_count = shape[1] if len(shape) > 1 else len(columns)

    controls: list[ft.Control] = []

    # ── 1. Header ──────────────────────────────────────────────
    header_row = ft.Row(
        [
            ft.Row(
                [
                    ft.Icon(
                        ft.Icons.DATASET_ROUNDED,
                        size=20,
                        color=theme.ACCENT,
                    ),
                    ft.Text(
                        dataset_name or "Active Dataset",
                        size=tokens.FONT_MD,
                        weight=ft.FontWeight.W_700,
                    ),
                ],
                spacing=tokens.SPACE_XS,
            ),
            ft.Container(
                content=ft.Text(
                    f"{rows_count:,} rows × {cols_count} cols",
                    size=tokens.FONT_XS,
                    weight=ft.FontWeight.W_600,
                    color=theme.PRIMARY,
                ),
                padding=ft.Padding(
                    tokens.SPACE_SM, tokens.SPACE_XXS, tokens.SPACE_SM, tokens.SPACE_XXS
                ),
                bgcolor=ft.Colors.with_opacity(0.12, theme.PRIMARY),
                border_radius=tokens.RADIUS_SM,
            ),
        ],
        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
    )
    controls.append(header_row)

    # ── 2. AI Dataset Description Callout ───────────────────────
    if initial_description:
        controls.append(
            ft.Container(
                content=ft.Row(
                    [
                        ft.Icon(
                            ft.Icons.LIGHTBULB_ROUNDED,
                            size=18,
                            color=theme.ACCENT,
                        ),
                        ft.Text(
                            initial_description,
                            size=tokens.FONT_SM,
                            weight=ft.FontWeight.W_500,
                            color=ft.Colors.ON_SURFACE,
                            expand=True,
                        ),
                    ],
                    vertical_alignment=ft.CrossAxisAlignment.START,
                    spacing=tokens.SPACE_SM,
                ),
                padding=tokens.SPACE_MD,
                bgcolor=ft.Colors.with_opacity(0.08, theme.ACCENT),
                border_radius=tokens.RADIUS_MD,
                border=ft.Border.all(1, ft.Colors.with_opacity(0.2, theme.ACCENT)),
            )
        )

    # ── 3. Column Chips ─────────────────────────────────────────
    if columns:
        col_chips = []
        for col in columns[:20]:
            dtype = dtypes.get(col, "object")
            col_chips.append(
                ft.Container(
                    content=ft.Column(
                        [
                            ft.Text(
                                str(col)[:18],
                                size=tokens.FONT_XS,
                                weight=ft.FontWeight.W_600,
                                max_lines=1,
                                overflow=ft.TextOverflow.ELLIPSIS,
                            ),
                            ft.Text(
                                str(dtype),
                                size=9,
                                color=ft.Colors.ON_SURFACE_VARIANT,
                            ),
                        ],
                        spacing=1,
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    padding=ft.Padding(
                        tokens.SPACE_XS,
                        tokens.SPACE_XXS,
                        tokens.SPACE_XS,
                        tokens.SPACE_XXS,
                    ),
                    border_radius=tokens.RADIUS_SM,
                    bgcolor=ft.Colors.with_opacity(0.05, ft.Colors.ON_SURFACE),
                )
            )

        controls.append(
            ft.Column(
                [
                    ft.Row(
                        [
                            ft.Icon(
                                ft.Icons.VIEW_COLUMN_ROUNDED,
                                size=14,
                                color=theme.ACCENT,
                            ),
                            ft.Text(
                                f"Columns ({len(columns)})",
                                size=tokens.FONT_XS,
                                weight=ft.FontWeight.W_600,
                            ),
                        ],
                        spacing=tokens.SPACE_XXS,
                    ),
                    ft.Row(col_chips, wrap=True, spacing=tokens.SPACE_XXS),
                ],
                spacing=tokens.SPACE_XS,
            )
        )

    # ── 4. Statistical Summary (df.describe()) ──────────────────
    if summary_stats and isinstance(summary_stats, dict):
        try:
            stat_cols = [
                ft.DataColumn(
                    ft.Text(
                        "Stat",
                        size=tokens.FONT_XS,
                        weight=ft.FontWeight.W_600,
                    )
                )
            ]
            feature_names = list(summary_stats.keys())[:15]
            for col_name in feature_names:
                stat_cols.append(
                    ft.DataColumn(
                        ft.Text(
                            str(col_name)[:12],
                            size=tokens.FONT_XS,
                            weight=ft.FontWeight.W_600,
                        )
                    )
                )

            stat_keys = ["count", "mean", "std", "min", "25%", "50%", "75%", "max"]
            stat_rows = []
            for sk in stat_keys:
                cells = [
                    ft.DataCell(
                        ft.Text(
                            sk,
                            size=tokens.FONT_XS,
                            weight=ft.FontWeight.W_600,
                            color=theme.PRIMARY,
                        )
                    )
                ]
                has_any_val = False
                for fn in feature_names:
                    val = summary_stats[fn].get(sk, "")
                    if val != "" and val is not None:
                        has_any_val = True
                        val_str = (
                            f"{float(val):.2f}"
                            if isinstance(val, (int, float))
                            else str(val)
                        )
                    else:
                        val_str = "—"
                    cells.append(
                        ft.DataCell(
                            ft.Text(
                                val_str,
                                size=tokens.FONT_XS,
                                font_family="RobotoMono",
                            )
                        )
                    )
                if has_any_val:
                    stat_rows.append(ft.DataRow(cells=cells))

            if stat_rows:
                controls.append(
                    ft.Column(
                        [
                            ft.Row(
                                [
                                    ft.Icon(
                                        ft.Icons.QUERY_STATS_ROUNDED,
                                        size=14,
                                        color=theme.PRIMARY,
                                    ),
                                    ft.Text(
                                        "Statistical Summary (df.describe)",
                                        size=tokens.FONT_XS,
                                        weight=ft.FontWeight.W_600,
                                    ),
                                ],
                                spacing=tokens.SPACE_XXS,
                            ),
                            ft.Container(
                                content=ft.Row(
                                    [
                                        ft.DataTable(
                                            columns=stat_cols,
                                            rows=stat_rows,
                                            heading_row_height=36,
                                            data_row_max_height=32,
                                            column_spacing=18,
                                            horizontal_lines=ft.BorderSide(
                                                1,
                                                ft.Colors.with_opacity(
                                                    0.08, ft.Colors.ON_SURFACE
                                                ),
                                            ),
                                            border=ft.Border.all(
                                                1,
                                                ft.Colors.with_opacity(
                                                    0.12, ft.Colors.ON_SURFACE
                                                ),
                                            ),
                                            border_radius=tokens.RADIUS_SM,
                                        )
                                    ],
                                    scroll=ft.ScrollMode.AUTO,
                                ),
                                border_radius=tokens.RADIUS_SM,
                            ),
                        ],
                        spacing=tokens.SPACE_XS,
                    )
                )
        except Exception as ex:
            logger.debug("Summary stats table generation error: %s", ex)

    # ── 5. Starter Suggestion Chips ─────────────────────────────
    if suggestions and on_suggestion_selected:
        chips = []
        for s in suggestions[:5]:
            if isinstance(s, dict):
                label_txt = s.get("label") or s.get("prompt", "")
                icon_txt = s.get("icon", "✨")
                prompt_val = s.get("prompt") or label_txt
                disp = f"{icon_txt} {label_txt}".strip()
            else:
                prompt_val = str(s)
                disp = str(s)

            chips.append(
                ft.Chip(
                    label=ft.Text(disp, size=tokens.FONT_XS),
                    tooltip=prompt_val,
                    on_click=lambda _, p=prompt_val: on_suggestion_selected(p),
                )
            )

        controls.append(
            ft.Column(
                [
                    ft.Text(
                        "Recommended analyses to explore:",
                        size=tokens.FONT_XS,
                        weight=ft.FontWeight.W_600,
                        color=ft.Colors.ON_SURFACE_VARIANT,
                    ),
                    ft.Row(chips, wrap=True, spacing=tokens.SPACE_XXS),
                ],
                spacing=tokens.SPACE_XXS,
            )
        )

    return ft.Container(
        content=ft.Column(controls=controls, spacing=tokens.SPACE_SM),
        padding=tokens.SPACE_MD,
        border_radius=tokens.RADIUS_LG,
        bgcolor=theme.GLASS_BG,
        border=ft.Border.all(1, theme.GLASS_BORDER_COLOR),
        margin=ft.Margin(0, 0, 0, tokens.SPACE_SM),
    )
