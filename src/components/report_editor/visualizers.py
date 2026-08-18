"""Data and result visualizer controls for Report editor blocks."""

from __future__ import annotations

import flet as ft

from core import theme, tokens


def build_serialized_result_visualizer(ser_res) -> ft.Control | None:
    """Renders structured analysis output (DataFrames, Series, Dicts, Arrays, Charts) as native UI."""
    if not ser_res or not isinstance(ser_res, dict):
        return None

    res_type = ser_res.get("type")

    # 0. Native interactive chart (flet_charts) with static-PNG fallback
    if res_type == "chart":
        from components.native_chart import build_native_chart

        native = build_native_chart(ser_res.get("data") or {})
        if native is not None:
            return native
        png_b64 = ser_res.get("png_b64")
        if png_b64:
            # Worst-case fallback: render the Colab-generated matplotlib PNG
            # exactly like the legacy app displayed charts.
            return ft.Container(
                content=ft.Image(
                    src=png_b64,
                    fit=ft.BoxFit.CONTAIN,
                    border_radius=tokens.RADIUS_MD,
                ),
                alignment=ft.Alignment.CENTER,
                padding=ft.Padding(0, tokens.SPACE_XS, 0, tokens.SPACE_XS),
            )
        return None

    # 0.5 Scalar metric tile
    if res_type == "scalar":
        val = ser_res.get("data")
        if val is None:
            return None
        val_str = f"{val:.4f}" if isinstance(val, float) else str(val)
        return ft.Container(
            content=ft.Text(
                val_str,
                size=tokens.FONT_TITLE,
                weight=ft.FontWeight.BOLD,
                color=theme.PRIMARY,
            ),
            padding=ft.Padding(12, 8, 12, 8),
            alignment=ft.Alignment.CENTER,
            border_radius=tokens.RADIUS_MD,
            bgcolor=ft.Colors.with_opacity(0.05, theme.PRIMARY),
            border=ft.Border.all(1, theme.GLASS_BORDER_COLOR),
        )

    # 1. DataFrame or Series Table
    if res_type in ("dataframe", "series"):
        cols_data = ser_res.get("columns") or []
        rows_data = ser_res.get("data") or []

        if res_type == "series":
            name = ser_res.get("name") or "Value"
            index_data = ser_res.get("index") or []
            cols_data = ["Index", name]
            rows_data = [[idx, val] for idx, val in zip(index_data, rows_data)]

        if not cols_data:
            return None

        columns = [
            ft.DataColumn(
                ft.Text(str(col), size=tokens.FONT_XS - 1, weight=ft.FontWeight.W_600)
            )
            for col in cols_data
        ]

        rows = []
        for row in rows_data:
            cells = []
            for cell in row:
                if isinstance(cell, float):
                    val_str = f"{cell:.4f}"
                else:
                    val_str = str(cell if cell is not None else "—")
                cells.append(
                    ft.DataCell(
                        ft.Text(
                            val_str,
                            size=tokens.FONT_XS - 1,
                            max_lines=1,
                            overflow=ft.TextOverflow.ELLIPSIS,
                        )
                    )
                )
            rows.append(ft.DataRow(cells=cells))

        table = ft.DataTable(
            columns=columns,
            rows=rows,
            border=ft.Border.all(1, ft.Colors.with_opacity(0.1, ft.Colors.ON_SURFACE)),
            border_radius=tokens.RADIUS_MD,
            horizontal_lines=ft.BorderSide(
                1, ft.Colors.with_opacity(0.06, ft.Colors.ON_SURFACE)
            ),
            column_spacing=tokens.SPACE_MD,
            heading_row_height=32,
            data_row_max_height=30,
        )

        total_rows = ser_res.get("total_rows", len(rows_data))
        footer_text = f"{total_rows:,} rows"
        if total_rows > len(rows_data):
            footer_text = f"Showing {len(rows_data)} of {total_rows:,} rows"

        return ft.Column(
            [
                ft.Container(
                    content=ft.Row([table], scroll=ft.ScrollMode.AUTO),
                    border_radius=tokens.RADIUS_MD,
                ),
                ft.Container(
                    content=ft.Text(
                        footer_text,
                        size=tokens.FONT_XS - 2,
                        color=ft.Colors.ON_SURFACE_VARIANT,
                        italic=True,
                    ),
                    padding=ft.Padding(4, 0, 0, 0),
                ),
            ],
            spacing=4,
        )

    # 2. Dictionary / Metrics
    if res_type == "dict":
        sub_data = ser_res.get("data") or {}
        primitives = {}
        structures = {}
        for k, v in sub_data.items():
            if isinstance(v, dict) and "type" in v:
                structures[k] = v
            else:
                primitives[k] = v

        controls = []
        if primitives:
            metric_cards = []
            for k, v in primitives.items():
                if isinstance(v, float):
                    val_str = f"{v:.4f}"
                else:
                    val_str = str(v if v is not None else "—")

                label_text = str(k).replace("_", " ").title()
                metric_cards.append(
                    ft.Container(
                        content=ft.Column(
                            [
                                ft.Text(
                                    label_text,
                                    size=tokens.FONT_XS - 2,
                                    color=ft.Colors.ON_SURFACE_VARIANT,
                                    weight="w600",
                                    max_lines=1,
                                    overflow="ellipsis",
                                ),
                                ft.Text(
                                    val_str,
                                    size=tokens.FONT_LG,
                                    weight="bold",
                                    color=theme.PRIMARY,
                                ),
                            ],
                            spacing=1,
                        ),
                        padding=8,
                        border_radius=tokens.RADIUS_SM,
                        bgcolor=ft.Colors.with_opacity(0.04, ft.Colors.ON_SURFACE),
                        border=ft.Border.all(1, theme.GLASS_BORDER_COLOR),
                        expand=True,
                    )
                )
            for c in metric_cards:
                c.col = {"xs": 6, "sm": 4}
            controls.append(
                ft.ResponsiveRow(
                    controls=metric_cards,
                    spacing=6,
                    run_spacing=6,
                )
            )

        if structures:
            for k, v in structures.items():
                label_text = str(k).replace("_", " ").title()
                sub_vis = build_serialized_result_visualizer(v)
                if sub_vis:
                    controls.append(
                        ft.Column(
                            [
                                ft.Row(
                                    [
                                        ft.Icon(
                                            ft.Icons.QUERY_STATS_ROUNDED,
                                            size=12,
                                            color=theme.ACCENT,
                                        ),
                                        ft.Text(
                                            label_text,
                                            size=tokens.FONT_XS,
                                            weight="bold",
                                            color=theme.ACCENT,
                                        ),
                                    ],
                                    spacing=4,
                                ),
                                sub_vis,
                            ],
                            spacing=2,
                        )
                    )

        if controls:
            return ft.Column(controls, spacing=8)

    # 3. Ndarray / List
    if res_type in ("ndarray", "list"):
        list_data = ser_res.get("data") or []
        if not list_data:
            return None

        if all(isinstance(x, dict) and "type" in x for x in list_data):
            sub_controls = []
            for x in list_data:
                vis = build_serialized_result_visualizer(x)
                if vis:
                    sub_controls.append(vis)
            return ft.Column(sub_controls, spacing=6)

        if len(list_data) <= 12 and all(isinstance(x, (int, float)) for x in list_data):
            chips = []
            for x in list_data:
                val_str = f"{x:.4f}" if isinstance(x, float) else str(x)
                chips.append(
                    ft.Container(
                        content=ft.Text(
                            val_str, size=tokens.FONT_XS - 1, font_family="RobotoMono"
                        ),
                        padding=ft.Padding(6, 3, 6, 3),
                        border_radius=4,
                        bgcolor=ft.Colors.with_opacity(0.06, theme.PRIMARY),
                    )
                )
            return ft.Row(chips, spacing=4, wrap=True)
        else:
            arr_str = ", ".join(
                f"{x:.4f}" if isinstance(x, float) else str(x) for x in list_data[:50]
            )
            if len(list_data) > 50:
                arr_str += f" ... (+{len(list_data) - 50} more items)"
            return ft.Container(
                content=ft.Text(
                    arr_str,
                    size=tokens.FONT_XS - 1,
                    font_family="RobotoMono",
                    color="#E0E0E0",
                ),
                padding=8,
                bgcolor="#0D0D1A",
                border_radius=tokens.RADIUS_SM,
            )

    return None
