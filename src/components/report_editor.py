"""Report block editor — reorderable block cards with AI editing."""

from __future__ import annotations

import flet as ft

from core import theme, tokens


def build_serialized_result_visualizer(ser_res) -> ft.Control | None:
    if not ser_res or not isinstance(ser_res, dict):
        return None

    res_type = ser_res.get("type")

    # 1. DataFrame or Series Table
    if res_type in ("dataframe", "series"):
        cols_data = ser_res.get("columns") or []
        rows_data = ser_res.get("data") or []

        # Fallback for Series
        if res_type == "series":
            name = ser_res.get("name") or "Value"
            index_data = ser_res.get("index") or []
            cols_data = ["Index", name]
            rows_data = [[idx, val] for idx, val in zip(index_data, rows_data)]

        if not cols_data:
            return None

        # Build elegant DataColumns
        columns = [
            ft.DataColumn(
                ft.Text(str(col), size=tokens.FONT_XS - 1, weight=ft.FontWeight.W_600)
            )
            for col in cols_data
        ]

        # Build elegant DataRows
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

    # 2. Dictionary
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
                    metric_cards,
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


def build_report_block_card(
    block: dict,
    index: int,
    total: int,
    on_change,
    on_move,
    on_delete,
) -> ft.Container:
    """Render one editable report block card with reorder arrows and delete action."""

    def _update_prompt(val):
        block["prompt"] = val

    def _update_desc(val):
        block["description"] = val
        on_change()

    # Chart image
    chart_widget = ft.Container(height=0)
    if block.get("figure_png_b64"):
        chart_widget = ft.Container(
            content=ft.Image(
                src=f"data:image/png;base64,{block['figure_png_b64']}",
                fit="contain",
                expand=True,
            ),
            height=240,
            border_radius=tokens.RADIUS_MD,
            clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
        )

    # Serialized result table or metrics
    res_widget = ft.Container(height=0)
    ser_res = block.get("serialized_result")
    stdout_val = block.get("stdout")

    if ser_res:
        vis = build_serialized_result_visualizer(ser_res)
        if vis:
            res_widget = ft.Container(
                content=vis,
                padding=tokens.SPACE_SM,
                border_radius=tokens.RADIUS_MD,
                bgcolor=ft.Colors.with_opacity(0.01, ft.Colors.ON_SURFACE),
            )
    elif stdout_val and str(stdout_val).strip() and str(stdout_val).strip() != "None":
        res_widget = ft.Container(
            content=ft.Text(
                str(stdout_val).strip(),
                size=10,
                font_family="RobotoMono",
                color="#E0E0E0",
            ),
            padding=tokens.SPACE_MD,
            bgcolor="#0D0D1A",
            border_radius=tokens.RADIUS_MD,
        )

    controls = [
        # Header with number + prompt
        ft.Row(
            [
                ft.Container(
                    content=ft.Text(
                        str(index + 1),
                        size=tokens.FONT_SM,
                        weight=ft.FontWeight.W_700,
                        color=ft.Colors.WHITE,
                        text_align=ft.TextAlign.CENTER,
                    ),
                    width=28,
                    height=28,
                    border_radius=14,
                    bgcolor=theme.PRIMARY,
                    alignment=ft.Alignment.CENTER,
                ),
                ft.TextField(
                    value=block.get("prompt", ""),
                    border="none",
                    text_size=14,
                    text_style=ft.TextStyle(weight=ft.FontWeight.W_600),
                    expand=True,
                    content_padding=ft.Padding(4, 0, 4, 0),
                    max_lines=2,
                    on_change=lambda e: _update_prompt(e.control.value),
                ),
            ],
            spacing=tokens.SPACE_MD,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        # Chart
        chart_widget,
        # Serialized result / table / metrics
        res_widget,
        # Description
        ft.Container(
            content=ft.Row(
                [
                    ft.Icon(
                        ft.Icons.LIGHTBULB_OUTLINE_ROUNDED,
                        size=tokens.ICON_SM,
                        color=theme.ACCENT,
                    ),
                    ft.TextField(
                        value=block.get("description", ""),
                        multiline=True,
                        border=ft.InputBorder.NONE,
                        content_padding=0,
                        text_size=13,
                        expand=True,
                        on_change=lambda e: _update_desc(e.control.value),
                    ),
                ],
                spacing=tokens.SPACE_SM,
                vertical_alignment=ft.CrossAxisAlignment.START,
            ),
            padding=tokens.SPACE_MD,
            border_radius=tokens.RADIUS_MD,
            bgcolor=ft.Colors.with_opacity(0.04, theme.ACCENT),
        ),
        # Reorder arrows and delete action
        ft.Row(
            [
                ft.IconButton(
                    ft.Icons.ARROW_UPWARD_ROUNDED,
                    icon_size=16,
                    disabled=index == 0,
                    on_click=lambda e, idx=index: on_move(idx, -1),
                    tooltip="Move up",
                ),
                ft.IconButton(
                    ft.Icons.ARROW_DOWNWARD_ROUNDED,
                    icon_size=16,
                    disabled=index == total - 1,
                    on_click=lambda e, idx=index: on_move(idx, 1),
                    tooltip="Move down",
                ),
                ft.IconButton(
                    ft.Icons.DELETE_OUTLINE_ROUNDED,
                    icon_size=16,
                    icon_color=theme.ERROR,
                    on_click=lambda e, idx=index: on_delete(idx),
                    tooltip="Delete block",
                ),
                ft.Container(expand=True),
                ft.Text(
                    f"Block {index + 1} of {total}",
                    size=11,
                    color=ft.Colors.ON_SURFACE_VARIANT,
                ),
            ],
            spacing=0,
        ),
    ]

    return ft.Container(
        content=ft.Column(controls, spacing=8),
        padding=14,
        border_radius=12,
        bgcolor=ft.Colors.with_opacity(0.04, ft.Colors.ON_SURFACE),
        border=ft.Border.all(1, theme.GLASS_BORDER_COLOR),
    )


def build_report_editor(
    blocks: list[dict],
    title: str,
    description: str,
    on_blocks_changed,
    on_title_changed,
    on_desc_changed,
    on_save,
    on_share,
    on_view_live,
    on_back,
    on_import,
    on_ai_edit,
    on_voice_toggle,
    is_saving: bool = False,
    is_sharing: bool = False,
    is_viewing_live: bool = False,
    is_deleting: bool = False,
    is_recording: bool = False,
    is_transcribing: bool = False,
    is_ai_editing: bool = False,
    is_public: bool = False,
    on_public_changed=None,
    recording_time: int = 0,
    ai_prompt_text: str = "",
    recording_timer_ref: ft.Ref[ft.Text] | None = None,
    save_btn_ref: ft.Ref[ft.Control] | None = None,
    share_btn_ref: ft.Ref[ft.Control] | None = None,
    view_live_btn_ref: ft.Ref[ft.Control] | None = None,
    on_delete=None,
) -> list[ft.Control]:
    """Build the full report editor UI. Returns list of controls."""
    controls = []

    # Header
    controls.append(
        ft.Container(
            content=ft.Column(
                [
                    ft.Text("Edit Report", weight="bold", size=16),
                    ft.TextField(
                        value=title,
                        label="Report Title",
                        border_radius=10,
                        on_change=lambda e: on_title_changed(e.control.value),
                    ),
                    ft.TextField(
                        value=description,
                        label="Description",
                        border_radius=10,
                        max_lines=3,
                        on_change=lambda e: on_desc_changed(e.control.value),
                    ),
                ],
                spacing=8,
            ),
            padding=20,
            margin=ft.Margin(20, 10, 20, 4),
            border_radius=16,
            bgcolor=theme.GLASS_BG,
            border=ft.Border.all(1, theme.GLASS_BORDER_COLOR),
        )
    )

    # Block cards
    total = len(blocks)

    def _move(idx, direction):
        j = idx + direction
        if 0 <= j < total:
            blocks[idx], blocks[j] = blocks[j], blocks[idx]
            on_blocks_changed()

    def _delete(idx):
        if 0 <= idx < len(blocks):
            blocks.pop(idx)
            on_blocks_changed()

    for i, block in enumerate(blocks):
        controls.append(
            ft.Container(
                content=build_report_block_card(
                    block, i, total, on_blocks_changed, _move, _delete
                ),
                margin=ft.Margin(20, 4, 20, 4),
            )
        )

    # Import from Analysis button
    controls.append(
        ft.Container(
            content=ft.OutlinedButton(
                "Import Block from Analysis",
                icon=ft.Icons.ADD_CHART_ROUNDED,
                on_click=lambda e: on_import(),
                style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10)),
            ),
            padding=ft.Padding(20, 4, 20, 4),
        )
    )

    # AI edit section
    ai_field_ref = ft.Ref[ft.TextField]()
    controls.append(
        ft.Container(
            content=ft.Column(
                [
                    ft.Text("Edit with AI", weight="bold", size=13, color=theme.ACCENT),
                    ft.Row(
                        [
                            ft.TextField(
                                ref=ai_field_ref,
                                value=ai_prompt_text,
                                hint_text="e.g. 'Make descriptions more academic', 'Reorder by importance'...",
                                border_radius=10,
                                max_lines=2,
                                expand=True,
                                text_size=13,
                                disabled=is_ai_editing or is_recording,
                                on_change=lambda e: on_ai_edit(
                                    "__set_text__", e.control.value
                                ),
                            ),
                            ft.Row(
                                [
                                    ft.Text(
                                        ref=recording_timer_ref,
                                        value=f"00:{recording_time:02d} / 01:00",
                                        size=11,
                                        color=theme.ERROR,
                                        weight="bold",
                                        visible=is_recording,
                                    ),
                                    ft.IconButton(
                                        ft.Icons.STOP_ROUNDED
                                        if is_recording
                                        else ft.Icons.MIC_ROUNDED,
                                        icon_color=theme.ERROR
                                        if is_recording
                                        else theme.ACCENT,
                                        tooltip="Stop" if is_recording else "Voice",
                                        on_click=on_voice_toggle,
                                        disabled=is_ai_editing,
                                    ),
                                ],
                                spacing=2,
                                vertical_alignment="center",
                            ),
                            ft.IconButton(
                                ft.Icons.AUTO_FIX_HIGH_ROUNDED,
                                icon_color=theme.ACCENT,
                                tooltip="Apply AI edit",
                                on_click=lambda e: on_ai_edit(
                                    "__submit__",
                                    ai_field_ref.current.value
                                    if ai_field_ref.current
                                    else "",
                                ),
                                disabled=is_ai_editing or is_recording,
                            ),
                        ],
                        spacing=4,
                        vertical_alignment="center",
                    ),
                    ft.ProgressBar(visible=is_ai_editing or is_transcribing),
                    ft.Row(
                        [
                            ft.ProgressRing(width=16, height=16, stroke_width=2),
                            ft.Text(
                                "Transcribing your voice..."
                                if is_transcribing
                                else "AI is editing your report...",
                                size=12,
                                color=theme.ACCENT,
                            ),
                        ],
                        spacing=8,
                        alignment="center",
                        visible=is_transcribing or is_ai_editing,
                    ),
                    ft.Divider(height=1, color=theme.GLASS_BORDER_COLOR),
                    # Row 1 — Primary actions
                    ft.Row(
                        [
                            ft.FilledButton(
                                ref=view_live_btn_ref,
                                content=ft.Row(
                                    [
                                        ft.ProgressRing(
                                            width=12,
                                            height=12,
                                            stroke_width=2,
                                            color="white",
                                        ),
                                        ft.Text("Opening...", size=12),
                                    ],
                                    spacing=6,
                                )
                                if is_viewing_live
                                else "View Live Report",
                                icon=ft.Icons.OPEN_IN_NEW_ROUNDED
                                if not is_viewing_live
                                else None,
                                style=ft.ButtonStyle(
                                    bgcolor=theme.PRIMARY,
                                    color=ft.Colors.WHITE,
                                    shape=ft.RoundedRectangleBorder(radius=12),
                                    padding=14,
                                ),
                                on_click=lambda e: on_view_live(),
                                disabled=is_viewing_live or is_ai_editing,
                                expand=True,
                            ),
                        ],
                        spacing=8,
                    ),
                    # Row 2 — Secondary actions
                    ft.Row(
                        [
                            ft.OutlinedButton(
                                content=ft.Row(
                                    [
                                        ft.ProgressRing(
                                            width=12, height=12, stroke_width=2
                                        ),
                                        ft.Text("Back...", size=12),
                                    ],
                                    spacing=6,
                                )
                                if is_deleting
                                else "Back",
                                icon=ft.Icons.ARROW_BACK_ROUNDED
                                if not is_deleting
                                else None,
                                style=ft.ButtonStyle(
                                    shape=ft.RoundedRectangleBorder(radius=12),
                                    padding=14,
                                ),
                                on_click=lambda e: on_back(),
                                disabled=is_deleting,
                            ),
                            ft.FilledButton(
                                ref=save_btn_ref,
                                content=ft.Row(
                                    [
                                        ft.ProgressRing(
                                            width=12,
                                            height=12,
                                            stroke_width=2,
                                            color="white",
                                        ),
                                        ft.Text("Saving...", size=12),
                                    ],
                                    spacing=6,
                                )
                                if is_saving
                                else "Save",
                                icon=ft.Icons.SAVE_ROUNDED if not is_saving else None,
                                style=ft.ButtonStyle(
                                    bgcolor=theme.PRIMARY,
                                    color=ft.Colors.WHITE,
                                    shape=ft.RoundedRectangleBorder(radius=12),
                                    padding=14,
                                ),
                                on_click=lambda e: on_save(),
                                disabled=is_saving or is_ai_editing,
                            ),
                            ft.Container(
                                content=ft.Row(
                                    [
                                        ft.Icon(
                                            ft.Icons.PUBLIC_ROUNDED,
                                            size=16,
                                            color=theme.PRIMARY
                                            if is_public
                                            else ft.Colors.ON_SURFACE_VARIANT,
                                        ),
                                        ft.Text(
                                            "Feature on spaninsight.com",
                                            size=12,
                                            expand=True,
                                            color=theme.PRIMARY
                                            if is_public
                                            else ft.Colors.ON_SURFACE_VARIANT,
                                        ),
                                        ft.Switch(
                                            value=is_public,
                                            on_change=lambda e: (
                                                on_public_changed(e.control.value)
                                                if on_public_changed
                                                else None
                                            ),
                                        ),
                                    ],
                                    spacing=8,
                                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                                ),
                                padding=ft.Padding(12, 8, 12, 8),
                                border_radius=8,
                                bgcolor=ft.Colors.with_opacity(0.05, theme.PRIMARY)
                                if is_public
                                else None,
                            ),
                            ft.OutlinedButton(
                                ref=share_btn_ref,
                                content=ft.Row(
                                    [
                                        ft.ProgressRing(
                                            width=12, height=12, stroke_width=2
                                        ),
                                        ft.Text("Sharing...", size=12),
                                    ],
                                    spacing=6,
                                )
                                if is_sharing
                                else "Share",
                                icon=ft.Icons.SHARE_ROUNDED if not is_sharing else None,
                                style=ft.ButtonStyle(
                                    shape=ft.RoundedRectangleBorder(radius=12),
                                    padding=14,
                                    color=theme.PRIMARY,
                                ),
                                on_click=lambda e: on_share(),
                                disabled=is_sharing or is_ai_editing,
                            ),
                        ]
                        + (
                            [
                                ft.OutlinedButton(
                                    content=ft.Row(
                                        [
                                            ft.ProgressRing(
                                                width=12,
                                                height=12,
                                                stroke_width=2,
                                                color=theme.ERROR,
                                            ),
                                            ft.Text(
                                                "Deleting...",
                                                size=12,
                                                color=theme.ERROR,
                                            ),
                                        ],
                                        spacing=6,
                                    )
                                    if is_deleting
                                    else "Delete Report",
                                    icon=ft.Icons.DELETE_FOREVER_ROUNDED
                                    if not is_deleting
                                    else None,
                                    icon_color=theme.ERROR,
                                    style=ft.ButtonStyle(
                                        color=theme.ERROR,
                                        shape=ft.RoundedRectangleBorder(radius=12),
                                        padding=14,
                                    ),
                                    on_click=lambda e: on_delete(),
                                    disabled=is_deleting or is_ai_editing,
                                )
                            ]
                            if on_delete is not None
                            else []
                        ),
                        spacing=8,
                        wrap=True,
                    ),
                ],
                spacing=8,
            ),
            padding=20,
            margin=ft.Margin(20, 8, 20, 8),
            border_radius=16,
            bgcolor=theme.GLASS_BG,
            border=ft.Border.all(1, theme.GLASS_BORDER_COLOR),
        )
    )

    controls.append(ft.Container(height=100))
    return controls
