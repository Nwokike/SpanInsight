"""DatasetOverviewCard — SpanInsight's rich initial dataset overview component.

Renders dataset shape, memory footprint, column type chips with null badges,
dynamic statistical summary table (df.describe() with categorical + numeric support),
and initial AI starter suggestions.
"""

from __future__ import annotations

import logging
import math
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
    on_inspect_schema: Callable[[], None] | None = None,
) -> ft.Container:
    """Build a rich glassmorphic Dataset Overview Card."""
    columns = schema.get("columns", [])
    dtypes = schema.get("dtypes", {})
    nulls = schema.get("nulls", {})
    shape = schema.get("shape", [0, 0])
    summary_stats = schema.get("summary", {})

    rows_count = shape[0] if len(shape) > 0 else 0
    cols_count = shape[1] if len(shape) > 1 else len(columns)

    controls: list[ft.Control] = []

    # ── 1. Header ──────────────────────────────────────────────
    header_right_controls: list[ft.Control] = [
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
        )
    ]

    if on_view_raw_data:
        header_right_controls.append(
            ft.IconButton(
                icon=ft.Icons.TABLE_VIEW_ROUNDED,
                tooltip="Preview Raw Data",
                icon_size=18,
                icon_color=theme.ACCENT,
                on_click=lambda _: on_view_raw_data(),
            )
        )

    if on_inspect_schema:
        header_right_controls.append(
            ft.IconButton(
                icon=ft.Icons.INFO_OUTLINE_ROUNDED,
                tooltip="Schema Details",
                icon_size=18,
                icon_color=ft.Colors.ON_SURFACE_VARIANT,
                on_click=lambda _: on_inspect_schema(),
            )
        )

    header_row = ft.Row(
        controls=[
            ft.Row(
                controls=[
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
            ft.Row(
                controls=header_right_controls,
                spacing=tokens.SPACE_XS,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
        ],
        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
    )
    controls.append(header_row)

    # ── 2. AI Dataset Description Callout ───────────────────────
    if initial_description and initial_description.strip():
        is_fallback = (
            "unavailable" in initial_description.lower()
            or "analyzing dataset" in initial_description.lower()
        )
        callout_color = ft.Colors.ON_SURFACE_VARIANT if is_fallback else theme.ACCENT
        callout_icon = (
            ft.Icons.INFO_OUTLINE_ROUNDED if is_fallback else ft.Icons.LIGHTBULB_ROUNDED
        )
        controls.append(
            ft.Container(
                content=ft.Row(
                    controls=[
                        ft.Icon(
                            callout_icon,
                            size=18,
                            color=callout_color,
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
                bgcolor=ft.Colors.with_opacity(0.08, callout_color),
                border_radius=tokens.RADIUS_MD,
                border=ft.Border.all(1, ft.Colors.with_opacity(0.2, callout_color)),
            )
        )

    # ── 3. Column Chips with Null Indicators ────────────────────
    if columns:
        col_chips = []
        for col in columns[:30]:
            col_str = str(col)
            dtype = dtypes.get(col_str, "object")
            null_ct = nulls.get(col_str, 0)
            null_badge_color = theme.ERROR if null_ct > 0 else theme.SUCCESS
            null_badge_txt = f"{null_ct:,} null" if null_ct > 0 else "0 null"

            col_chips.append(
                ft.Container(
                    content=ft.Column(
                        controls=[
                            ft.Text(
                                col_str[:18],
                                size=tokens.FONT_XS,
                                weight=ft.FontWeight.W_600,
                                max_lines=1,
                                overflow=ft.TextOverflow.ELLIPSIS,
                            ),
                            ft.Row(
                                controls=[
                                    ft.Text(
                                        str(dtype),
                                        size=9,
                                        color=ft.Colors.ON_SURFACE_VARIANT,
                                    ),
                                    ft.Container(
                                        content=ft.Text(
                                            null_badge_txt,
                                            size=8,
                                            weight=ft.FontWeight.W_700,
                                            color=null_badge_color,
                                        ),
                                        padding=ft.Padding(3, 0, 3, 0),
                                        bgcolor=ft.Colors.with_opacity(
                                            0.12, null_badge_color
                                        ),
                                        border_radius=tokens.RADIUS_SM,
                                    ),
                                ],
                                spacing=4,
                                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                            ),
                        ],
                        spacing=2,
                        horizontal_alignment=ft.CrossAxisAlignment.START,
                    ),
                    padding=ft.Padding(
                        tokens.SPACE_XS,
                        tokens.SPACE_XXS,
                        tokens.SPACE_XS,
                        tokens.SPACE_XXS,
                    ),
                    border_radius=tokens.RADIUS_SM,
                    bgcolor=ft.Colors.with_opacity(0.05, ft.Colors.ON_SURFACE),
                    border=ft.Border.all(
                        1, ft.Colors.with_opacity(0.1, ft.Colors.ON_SURFACE)
                    ),
                )
            )

        controls.append(
            ft.Column(
                controls=[
                    ft.Row(
                        controls=[
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
                    ft.Row(controls=col_chips, wrap=True, spacing=tokens.SPACE_XXS),
                ],
                spacing=tokens.SPACE_XS,
            )
        )

    # ── 4. Dynamic Statistical Summary (df.describe()) ──────────
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
            total_features = len(summary_stats)
            feature_names = list(summary_stats.keys())[:30]
            hidden_cols = total_features - len(feature_names)
            for col_name in feature_names:
                stat_cols.append(
                    ft.DataColumn(
                        ft.Text(
                            str(col_name)[:14],
                            size=tokens.FONT_XS,
                            weight=ft.FontWeight.W_600,
                        )
                    )
                )

            # Discover all statistic keys across features (both numerical and categorical)
            ordered_standard = [
                "count",
                "unique",
                "top",
                "freq",
                "mean",
                "std",
                "min",
                "25%",
                "50%",
                "75%",
                "max",
            ]
            discovered_keys: list[str] = []
            for fn in feature_names:
                feat_dict = summary_stats.get(fn)
                if isinstance(feat_dict, dict):
                    for k in feat_dict:
                        k_str = str(k)
                        if k_str not in discovered_keys:
                            discovered_keys.append(k_str)

            stat_keys = [k for k in ordered_standard if k in discovered_keys] + [
                k for k in discovered_keys if k not in ordered_standard
            ]

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
                    feat_dict = summary_stats.get(fn, {})
                    val = feat_dict.get(sk, "") if isinstance(feat_dict, dict) else ""
                    if val != "" and val is not None:
                        if isinstance(val, float):
                            if math.isnan(val) or math.isinf(val):
                                val_str = "—"
                            elif val == int(val):
                                val_str = f"{int(val):,}"
                                has_any_val = True
                            else:
                                val_str = f"{val:.2f}"
                                has_any_val = True
                        elif isinstance(val, int):
                            val_str = f"{val:,}"
                            has_any_val = True
                        else:
                            s = str(val)
                            val_str = s[:16] + "…" if len(s) > 16 else s
                            has_any_val = True
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
                        controls=[
                            ft.Row(
                                controls=[
                                    ft.Icon(
                                        ft.Icons.QUERY_STATS_ROUNDED,
                                        size=14,
                                        color=theme.PRIMARY,
                                    ),
                                    ft.Text(
                                        "Statistical Summary (df.describe)"
                                        + (
                                            f" · +{hidden_cols} more cols"
                                            if hidden_cols > 0
                                            else ""
                                        ),
                                        size=tokens.FONT_XS,
                                        weight=ft.FontWeight.W_600,
                                    ),
                                ],
                                spacing=tokens.SPACE_XXS,
                            ),
                            ft.Container(
                                content=ft.Row(
                                    controls=[
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

    return ft.Container(
        content=ft.Column(controls=controls, spacing=tokens.SPACE_SM),
        padding=tokens.SPACE_MD,
        border_radius=tokens.RADIUS_LG,
        bgcolor=theme.GLASS_BG,
        border=ft.Border.all(1, theme.GLASS_BORDER_COLOR),
        margin=ft.Margin(0, 0, 0, tokens.SPACE_SM),
    )
