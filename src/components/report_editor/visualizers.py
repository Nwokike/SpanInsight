"""Data and result visualizer controls for Report editor blocks."""

from __future__ import annotations

import flet as ft

from core import theme, tokens


def build_serialized_result_visualizer(ser_res) -> ft.Control | None:
    """Renders structured analysis output (DataFrames, Series, Dicts, Arrays, Charts) as native UI."""
    if not ser_res or not isinstance(ser_res, dict):
        return None

    # Handle direct chart spec: {"type": "bar"|"line"|"pie", ...}
    res_type = ser_res.get("type")
    if res_type in ("bar", "line", "pie"):
        from components.native_chart import build_native_chart

        return build_native_chart(ser_res)

    # Handle {"chart": {...}} embedded inside result dict
    if "chart" in ser_res and isinstance(ser_res["chart"], dict):
        from components.native_chart import build_native_chart

        chart_ctrl = build_native_chart(ser_res["chart"])
        if chart_ctrl is not None:
            other_entries = {k: v for k, v in ser_res.items() if k != "chart"}
            if not other_entries:
                return chart_ctrl
            from services.ai.analysis.serializer import serialize_data

            other_vis = build_serialized_result_visualizer(
                serialize_data(other_entries)
            )
            if other_vis is not None:
                return ft.Column([chart_ctrl, other_vis], spacing=tokens.SPACE_SM)
            return chart_ctrl

    # 0. Native interactive chart (flet_charts) with static-PNG fallback
    if res_type == "chart":
        from components.native_chart import build_native_chart

        chart_spec = (
            ser_res.get("data") if isinstance(ser_res.get("data"), dict) else ser_res
        )
        native = build_native_chart(chart_spec)
        if native is not None:
            return native
        png_b64 = ser_res.get("png_b64")
        if png_b64:
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
            padding=ft.Padding(
                tokens.SPACE_MD, tokens.SPACE_SM, tokens.SPACE_MD, tokens.SPACE_SM
            ),
            alignment=ft.Alignment.CENTER,
            border_radius=tokens.RADIUS_MD,
            bgcolor=ft.Colors.with_opacity(tokens.OPACITY_FAINT, theme.PRIMARY),
            border=ft.Border.all(tokens.DIVIDER_THICKNESS, theme.GLASS_BORDER_COLOR),
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
                ft.Text(str(col), size=tokens.FONT_XS, weight=ft.FontWeight.W_600)
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
                    val_str = str(cell if cell is not None else "-")
                cells.append(
                    ft.DataCell(
                        ft.Text(
                            val_str,
                            size=tokens.FONT_XS,
                            max_lines=1,
                            overflow=ft.TextOverflow.ELLIPSIS,
                        )
                    )
                )
            rows.append(ft.DataRow(cells=cells))

        table = ft.DataTable(
            columns=columns,
            rows=rows,
            border=ft.Border.all(
                tokens.DIVIDER_THICKNESS,
                ft.Colors.with_opacity(tokens.OPACITY_LIGHT, ft.Colors.ON_SURFACE),
            ),
            border_radius=tokens.RADIUS_MD,
            horizontal_lines=ft.BorderSide(
                tokens.DIVIDER_THICKNESS,
                ft.Colors.with_opacity(tokens.OPACITY_SUBTLE, ft.Colors.ON_SURFACE),
            ),
            column_spacing=tokens.SPACE_MD,
            heading_row_height=tokens.TABLE_DATA_ROW_HEIGHT,
            data_row_max_height=tokens.TABLE_DATA_ROW_HEIGHT,
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
                        size=tokens.FONT_XXS,
                        color=ft.Colors.ON_SURFACE_VARIANT,
                        italic=True,
                    ),
                    padding=ft.Padding(
                        tokens.SPACE_XS,
                        tokens.SPACE_NONE,
                        tokens.SPACE_NONE,
                        tokens.SPACE_NONE,
                    ),
                ),
            ],
            spacing=tokens.SPACE_XS,
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
                    val_str = str(v if v is not None else "-")

                label_text = str(k).replace("_", " ").title()
                metric_cards.append(
                    ft.Container(
                        content=ft.Column(
                            [
                                ft.Text(
                                    label_text,
                                    size=tokens.FONT_XXS,
                                    color=ft.Colors.ON_SURFACE_VARIANT,
                                    weight=ft.FontWeight.W_600,
                                    max_lines=1,
                                    overflow=ft.TextOverflow.ELLIPSIS,
                                ),
                                ft.Text(
                                    val_str,
                                    size=tokens.FONT_LG,
                                    weight=ft.FontWeight.BOLD,
                                    color=theme.PRIMARY,
                                ),
                            ],
                            spacing=tokens.SPACE_MICRO,
                        ),
                        padding=tokens.SPACE_SM,
                        border_radius=tokens.RADIUS_SM,
                        bgcolor=ft.Colors.with_opacity(
                            tokens.OPACITY_SUBTLE, ft.Colors.ON_SURFACE
                        ),
                        border=ft.Border.all(
                            tokens.DIVIDER_THICKNESS, theme.GLASS_BORDER_COLOR
                        ),
                        expand=True,
                    )
                )
            for c in metric_cards:
                c.col = {"xs": 6, "sm": 4}
            controls.append(
                ft.ResponsiveRow(
                    controls=metric_cards,
                    spacing=tokens.SPACE_SM_XS,
                    run_spacing=tokens.SPACE_SM_XS,
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
                                            size=tokens.ICON_MICRO,
                                            color=theme.ACCENT,
                                        ),
                                        ft.Text(
                                            label_text,
                                            size=tokens.FONT_XS,
                                            weight="bold",
                                            color=theme.ACCENT,
                                        ),
                                    ],
                                    spacing=tokens.SPACE_XS,
                                ),
                                sub_vis,
                            ],
                            spacing=tokens.SPACE_XXS,
                        )
                    )

        if controls:
            return ft.Column(controls, spacing=tokens.SPACE_SM)

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
            return ft.Column(sub_controls, spacing=tokens.SPACE_SM_XS)

        if len(list_data) <= 12 and all(isinstance(x, (int, float)) for x in list_data):
            chips = []
            for x in list_data:
                val_str = f"{x:.4f}" if isinstance(x, float) else str(x)
                chips.append(
                    ft.Container(
                        content=ft.Text(
                            val_str, size=tokens.FONT_XS, font_family="RobotoMono"
                        ),
                        padding=ft.Padding(
                            tokens.SPACE_SM_XS,
                            tokens.SPACE_TINY,
                            tokens.SPACE_SM_XS,
                            tokens.SPACE_TINY,
                        ),
                        border_radius=tokens.RADIUS_XS,
                        bgcolor=ft.Colors.with_opacity(
                            tokens.OPACITY_SUBTLE, theme.PRIMARY
                        ),
                    )
                )
            return ft.Row(chips, spacing=tokens.SPACE_XS, wrap=True)
        else:
            arr_str = ", ".join(
                f"{x:.4f}" if isinstance(x, float) else str(x) for x in list_data[:50]
            )
            if len(list_data) > 50:
                arr_str += f" ... (+{len(list_data) - 50} more items)"
            return ft.Container(
                content=ft.Text(
                    arr_str,
                    size=tokens.FONT_XS,
                    font_family="RobotoMono",
                    color=theme.TERMINAL_TEXT_MUTED,
                ),
                padding=tokens.SPACE_SM,
                bgcolor=theme.TERMINAL_BG,
                border_radius=tokens.RADIUS_SM,
            )

    return None
