"""Data and result visualizer controls for Report editor blocks."""

from __future__ import annotations

import flet as ft

from core import theme, tokens

# Hard cap on rows rendered in any result table so huge payloads stay bounded.
_MAX_TABLE_ROWS = 100


def _scalar_str(v) -> str:
    """Compact string for a single scalar cell value."""
    if isinstance(v, float):
        return f"{v:.4f}"
    return str(v if v is not None else "-")


def _summarize_value(v, max_items: int = 5) -> str:
    """Short human-readable summary of a nested dict/list for a table cell."""
    if isinstance(v, dict):
        keys = list(v.keys())
        if len(keys) <= max_items:
            return "{" + ", ".join(str(k) for k in keys) + "}"
        shown = ", ".join(str(k) for k in keys[:max_items])
        return "{" + shown + f", … +{len(keys) - max_items} more}}"
    if isinstance(v, list):
        if len(v) <= max_items:
            return "[" + ", ".join(_scalar_str(x) for x in v) + "]"
        shown = ", ".join(_scalar_str(x) for x in v[:max_items])
        return "[" + shown + f", … +{len(v) - max_items} more]"
    return _scalar_str(v)


def _columnar_to_table(v) -> tuple[list, list] | None:
    """If ``v`` is a dict of equal-length scalar lists, return (columns, rows).

    This is the shape pandas ``to_dict(orient="list")`` produces, e.g.
    ``{"Missing Count": [5, 3], "Missing Percentage": [0.8, 0.5]}``. Returning a
    table here is what turns the ugly ``str()`` blob into a clean multi-column
    table. Anything that is not columnar returns ``None``.
    """
    if not isinstance(v, dict) or not v:
        return None
    vals = list(v.values())
    if not all(isinstance(x, list) and x for x in vals):
        return None
    lengths = {len(x) for x in vals}
    if len(lengths) != 1:
        return None
    if not all(
        item is None or isinstance(item, (int, float, str, bool))
        for x in vals
        for item in x
    ):
        return None
    columns = [str(k) for k in v]
    rows = [[x[i] for x in vals] for i in range(lengths.pop())]
    return columns, rows


def _build_result_table(
    columns: list,
    rows: list,
    total: int | None = None,
    unit: str = "rows",
) -> ft.Control | None:
    """Render (columns, rows) as a bounded, horizontally-scrollable DataTable.

    Shared by the dataframe/series, dict, and list/ndarray branches so every
    structured result gets the same clean table treatment instead of a text dump.
    """
    if not columns or not rows:
        return None

    col_controls = [
        ft.DataColumn(
            ft.Text(str(col), size=tokens.FONT_XS, weight=ft.FontWeight.W_600)
        )
        for col in columns
    ]

    data_rows = []
    for row in rows:
        cells = []
        for cell in row:
            cells.append(
                ft.DataCell(
                    ft.Text(
                        _scalar_str(cell),
                        size=tokens.FONT_XS,
                        max_lines=1,
                        overflow=ft.TextOverflow.ELLIPSIS,
                    )
                )
            )
        data_rows.append(ft.DataRow(cells=cells))

    table = ft.DataTable(
        columns=col_controls,
        rows=data_rows,
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

    total_rows = total if total is not None else len(rows)
    footer_text = f"{total_rows:,} {unit}"
    if total_rows > len(rows):
        footer_text = f"Showing {len(rows)} of {total_rows:,} {unit}"

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

        return _build_result_table(
            cols_data, rows_data, total=ser_res.get("total_rows")
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
            # Split primitives into columnar tables, flat scalars, and nested other.
            table_entries = {}
            scalar_entries = {}
            other_entries = {}
            for k, v in primitives.items():
                cols_rows = _columnar_to_table(v)
                if cols_rows is not None:
                    table_entries[k] = cols_rows
                elif isinstance(v, (dict, list)):
                    other_entries[k] = v
                else:
                    scalar_entries[k] = v

            # 2a. Columnar sub-dicts -> proper multi-column tables. This is the fix
            # for payloads like {"missing_values_summary": {"Missing Count": [...]}}.
            for k, (cols, rows) in table_entries.items():
                label_text = str(k).replace("_", " ").title()
                table = _build_result_table(cols, rows, total=len(rows))
                if table:
                    controls.append(
                        ft.Column(
                            [
                                ft.Text(
                                    label_text,
                                    size=tokens.FONT_XS,
                                    weight="bold",
                                    color=theme.ACCENT,
                                ),
                                table,
                            ],
                            spacing=tokens.SPACE_XXS,
                        )
                    )

            # 2b. Small flat scalars -> metric cards (the nice path for few numbers).
            use_cards = (
                not other_entries and scalar_entries and len(scalar_entries) <= 6
            )
            if use_cards:
                metric_cards = []
                for k, v in scalar_entries.items():
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
                                        _scalar_str(v),
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
            else:
                # 2c. Large or nested -> bounded Key/Value table instead of a blob.
                kv = dict(scalar_entries)
                kv.update(other_entries)
                if kv:
                    kv_rows = [
                        [
                            str(k),
                            _summarize_value(v)
                            if isinstance(v, (dict, list))
                            else _scalar_str(v),
                        ]
                        for k, v in kv.items()
                    ]
                    table = _build_result_table(
                        ["Key", "Value"], kv_rows, total=len(kv_rows), unit="entries"
                    )
                    if table:
                        controls.append(table)

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

        # Small numeric list -> chips (the nice path for few numbers).
        if len(list_data) <= 12 and all(isinstance(x, (int, float)) for x in list_data):
            chips = []
            for x in list_data:
                chips.append(
                    ft.Container(
                        content=ft.Text(
                            _scalar_str(x),
                            size=tokens.FONT_XS,
                            font_family="RobotoMono",
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

        # Everything else -> bounded table instead of a terminal text dump.
        if all(isinstance(x, dict) for x in list_data):
            col_names = []
            for x in list_data:
                for k in x:
                    if k not in col_names:
                        col_names.append(str(k))
            rows = [[x.get(c) for c in col_names] for x in list_data[:_MAX_TABLE_ROWS]]
            return _build_result_table(
                col_names, rows, total=len(list_data), unit="items"
            )

        rows = [[i, x] for i, x in enumerate(list_data[:_MAX_TABLE_ROWS])]
        return _build_result_table(
            ["Index", "Value"], rows, total=len(list_data), unit="items"
        )

    return None
