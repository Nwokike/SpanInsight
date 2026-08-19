"""Statistical summary DataTable (df.describe) for DatasetOverviewCard."""

from __future__ import annotations

import logging
import math

import flet as ft

from core import theme, tokens

logger = logging.getLogger("DatasetOverviewCard.SummaryTable")


def build_summary_table_section(summary_stats: dict) -> ft.Control | None:
    """Build a styled DataTable displaying dynamic statistical summaries."""
    if not summary_stats or not isinstance(summary_stats, dict):
        return None

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
                            val_str = "-"
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
                    val_str = "-"

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

        if not stat_rows:
            return None

        return ft.Column(
            controls=[
                ft.Row(
                    controls=[
                        ft.Icon(
                            ft.Icons.QUERY_STATS_ROUNDED,
                            size=tokens.ICON_XS,
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
                                heading_row_height=tokens.TABLE_HEADING_ROW_HEIGHT,
                                data_row_max_height=tokens.TABLE_DATA_ROW_HEIGHT,
                                column_spacing=tokens.TABLE_COLUMN_SPACING,
                                horizontal_lines=ft.BorderSide(
                                    tokens.DIVIDER_THICKNESS,
                                    ft.Colors.with_opacity(
                                        tokens.OPACITY_MUTED, ft.Colors.ON_SURFACE
                                    ),
                                ),
                                border=ft.Border.all(
                                    tokens.DIVIDER_THICKNESS,
                                    ft.Colors.with_opacity(
                                        tokens.OPACITY_CONTAINER, ft.Colors.ON_SURFACE
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
    except Exception as ex:
        logger.debug("Summary stats table generation error: %s", ex)
        return None
