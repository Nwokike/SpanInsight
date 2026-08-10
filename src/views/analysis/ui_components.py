import base64
import logging

import flet as ft

from components.data_preview import build_data_preview
from components.suggestion_chips import build_suggestion_chips
from core import theme, tokens
from core.state import state
from views.analysis.handlers import on_pin_block, on_rerun_code, on_suggestion_selected
from views.analysis.state import AnalysisState

logger = logging.getLogger(__name__)


def build_chart_container(block: dict) -> ft.Container | None:
    figure_png = block.get("figure_png")
    if not figure_png:
        return None
    try:
        b64_img = base64.b64encode(figure_png).decode("utf-8")
        return ft.Container(
            content=ft.Image(
                src=b64_img,
                fit="contain",
            ),
            height=280,
            alignment=ft.Alignment.CENTER,
        )
    except Exception as e:
        logger.error("Failed to render chart image: %s", e)
        return None


def build_result_visualizer(result_val, stdout_val) -> ft.Control | None:
    import numpy as np
    import pandas as pd

    if result_val is None:
        if (
            not stdout_val
            or not str(stdout_val).strip()
            or str(stdout_val).strip() == "None"
        ):
            return None
        return ft.Container(
            content=ft.Text(
                str(stdout_val).strip(),
                size=11,
                font_family="RobotoMono",
                color="#E0E0E0",
            ),
            padding=12,
            bgcolor="#0D0D1A",
            border_radius=8,
            border=ft.Border.all(1, "#1A1A2E"),
        )

    if isinstance(result_val, pd.DataFrame):
        if not result_val.empty:
            return build_data_preview(result_val)
        return ft.Text("Empty DataFrame", size=12, italic=True)

    if isinstance(result_val, pd.Series):
        if not result_val.empty:
            return build_data_preview(result_val.to_frame())
        return ft.Text("Empty Series", size=12, italic=True)

    if isinstance(result_val, np.ndarray) and result_val.ndim == 2:
        try:
            return build_data_preview(pd.DataFrame(result_val))
        except Exception:
            pass

    if isinstance(result_val, dict):
        primitives = {}
        structures = {}
        for k, v in result_val.items():
            if (
                isinstance(v, (int, float, str, bool, np.number))
                or (isinstance(v, np.ndarray) and v.ndim == 0)
                or (
                    isinstance(v, (list, tuple, np.ndarray))
                    and len(v) <= 24
                    and all(
                        isinstance(x, (int, float, str, bool, np.number)) for x in v
                    )
                )
            ):
                primitives[k] = v
            else:
                structures[k] = v

        controls = []

        if primitives:
            metric_cards = []
            for k, v in primitives.items():
                label_text = str(k).replace("_", " ").title()

                if isinstance(v, (list, tuple, np.ndarray)):
                    badge_items = []
                    for x in v:
                        val_str = (
                            f"{x:.4f}"
                            if isinstance(x, (float, np.floating))
                            else str(x)
                        )
                        badge_items.append(
                            ft.Container(
                                content=ft.Text(
                                    val_str,
                                    size=9,
                                    font_family="RobotoMono",
                                    color=theme.PRIMARY,
                                ),
                                padding=ft.Padding(5, 2, 5, 2),
                                bgcolor=ft.Colors.with_opacity(0.08, theme.PRIMARY),
                                border_radius=4,
                            )
                        )
                    card_content = ft.Column(
                        [
                            ft.Text(
                                label_text,
                                size=10,
                                color=ft.Colors.ON_SURFACE_VARIANT,
                                weight="w600",
                                max_lines=1,
                                overflow="ellipsis",
                            ),
                            ft.Row(
                                badge_items,
                                spacing=4,
                                wrap=True,
                            ),
                        ],
                        spacing=4,
                    )
                else:
                    if isinstance(v, (float, np.floating)):
                        val_str = f"{v:.4f}"
                    else:
                        val_str = str(v)

                    card_content = ft.Column(
                        [
                            ft.Text(
                                label_text,
                                size=10,
                                color=ft.Colors.ON_SURFACE_VARIANT,
                                weight="w600",
                                max_lines=1,
                                overflow="ellipsis",
                            ),
                            ft.Text(
                                val_str,
                                size=18,
                                weight="bold",
                                color=theme.PRIMARY,
                            ),
                        ],
                        spacing=2,
                    )

                metric_cards.append(
                    ft.Container(
                        content=card_content,
                        padding=12,
                        border_radius=8,
                        bgcolor=ft.Colors.with_opacity(0.04, ft.Colors.ON_SURFACE),
                        border=ft.Border.all(1, theme.GLASS_BORDER_COLOR),
                        expand=True,
                    )
                )

            for c in metric_cards:
                c.col = {"xs": 6, "sm": 4, "md": 3}
            controls.append(
                ft.ResponsiveRow(
                    metric_cards,
                    spacing=8,
                    run_spacing=8,
                )
            )

        if structures:
            for k, v in structures.items():
                label_text = str(k).replace("_", " ").title()
                sub_visualizer = build_result_visualizer(v, None)
                if sub_visualizer:
                    controls.append(
                        ft.Column(
                            [
                                ft.Row(
                                    [
                                        ft.Icon(
                                            ft.Icons.QUERY_STATS_ROUNDED,
                                            size=14,
                                            color=theme.ACCENT,
                                        ),
                                        ft.Text(
                                            label_text,
                                            size=12,
                                            weight="bold",
                                            color=theme.ACCENT,
                                        ),
                                    ],
                                    spacing=6,
                                    margin=ft.Margin(0, 4, 0, 2),
                                ),
                                sub_visualizer,
                            ],
                            spacing=4,
                        )
                    )

        if controls:
            return ft.Column(controls, spacing=12)

    if isinstance(result_val, (list, tuple, np.ndarray)):
        if (
            isinstance(result_val, (list, tuple))
            and len(result_val) > 0
            and all(isinstance(x, dict) for x in result_val)
        ):
            try:
                df = pd.DataFrame(result_val)
                return build_data_preview(df)
            except Exception:
                pass

        items = list(result_val)
        if len(items) == 0:
            return ft.Text("Empty list", size=12, italic=True)

        if len(items) <= 12 and all(
            isinstance(x, (int, float, np.number)) for x in items
        ):
            chips = []
            for x in items:
                val_str = f"{x:.4f}" if isinstance(x, (float, np.floating)) else str(x)
                chips.append(
                    ft.Container(
                        content=ft.Text(val_str, size=11, font_family="RobotoMono"),
                        padding=ft.Padding(8, 4, 8, 4),
                        border_radius=6,
                        bgcolor=ft.Colors.with_opacity(0.06, theme.PRIMARY),
                    )
                )
            return ft.Row(chips, spacing=4, wrap=True)
        else:
            arr_str = ", ".join(
                f"{x:.4f}" if isinstance(x, (float, np.floating)) else str(x)
                for x in items[:50]
            )
            if len(items) > 50:
                arr_str += f" ... (+{len(items) - 50} more items)"
            return ft.Container(
                content=ft.Text(
                    arr_str, size=11, font_family="RobotoMono", color="#E0E0E0"
                ),
                padding=10,
                bgcolor="#0D0D1A",
                border_radius=8,
            )

    val_str = str(result_val).strip()
    if not val_str or val_str == "None":
        return None

    return ft.Container(
        content=ft.Text(val_str, size=12, font_family="RobotoMono", color="#E0E0E0"),
        padding=10,
        bgcolor="#0D0D1A",
        border_radius=8,
    )


def build_text_output_container(result_val, stdout_val) -> ft.Container | None:
    try:
        visualizer = build_result_visualizer(result_val, stdout_val)
        if not visualizer:
            return None
        return ft.Container(
            content=visualizer,
            padding=ft.Padding(0, 8, 0, 8),
        )
    except Exception as e:
        logger.error("Failed to render result: %s", e)
        output_text = str(result_val) if result_val is not None else ""
        if not output_text or output_text.strip() == "None":
            output_text = str(stdout_val) if stdout_val is not None else ""
        if not output_text or not output_text.strip() or output_text.strip() == "None":
            return None
        return ft.Container(
            content=ft.Text(
                output_text, size=12, font_family="RobotoMono", color="#E0E0E0"
            ),
            padding=10,
            bgcolor="#0D0D1A",
            border_radius=8,
        )


def build_terminal(
    view_state: AnalysisState,
    code: str,
    block_index: int = -1,
    *,
    field_ref=None,
    on_run=None,
    filename="analysis.py",
) -> ft.Container:
    internal_field = ft.Ref[ft.TextField]()
    active_field = field_ref or internal_field

    def _on_run(e):
        if on_run:
            if active_field.current:
                on_run(active_field.current.value.strip())
        elif internal_field.current and block_index >= 0:
            new_code = internal_field.current.value
            view_state.page.run_task(on_rerun_code, view_state, block_index, new_code)

    show_run = on_run is not None or block_index >= 0

    return ft.Container(
        content=ft.Column(
            [
                ft.Container(
                    content=ft.Row(
                        [
                            ft.Row(
                                [
                                    ft.Container(
                                        width=8,
                                        height=8,
                                        border_radius=4,
                                        bgcolor="#FF5F57",
                                    ),
                                    ft.Container(
                                        width=8,
                                        height=8,
                                        border_radius=4,
                                        bgcolor="#FEBC2E",
                                    ),
                                    ft.Container(
                                        width=8,
                                        height=8,
                                        border_radius=4,
                                        bgcolor="#28C840",
                                    ),
                                ],
                                spacing=4,
                            ),
                            ft.Text(filename, size=10, color="#888888"),
                            ft.TextButton(
                                "▶ Run",
                                icon=ft.Icons.PLAY_ARROW_ROUNDED,
                                style=ft.ButtonStyle(color="#28C840"),
                                disabled=state.is_analyzing,
                                on_click=_on_run,
                            )
                            if show_run
                            else ft.Container(),
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    ),
                    padding=ft.Padding(10, 6, 10, 6),
                    bgcolor="#1A1A2E",
                    border_radius=ft.BorderRadius(
                        top_left=8, top_right=8, bottom_left=0, bottom_right=0
                    ),
                ),
                ft.Container(
                    content=ft.TextField(
                        ref=active_field,
                        value=code,
                        multiline=True,
                        min_lines=3,
                        max_lines=20,
                        text_size=11,
                        text_style=ft.TextStyle(
                            font_family="RobotoMono", color="#E0E0E0"
                        ),
                        border_color=ft.Colors.TRANSPARENT,
                        bgcolor=ft.Colors.TRANSPARENT,
                        cursor_color="#28C840",
                        filled=False,
                    ),
                    padding=ft.Padding(12, 6, 12, 12),
                    bgcolor="#0D0D1A",
                    border_radius=ft.BorderRadius(
                        top_left=0, top_right=0, bottom_left=8, bottom_right=8
                    ),
                ),
            ],
            spacing=0,
            horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
        ),
        margin=ft.Margin(0, 4, 0, 8),
    )


def build_block_card(
    view_state: AnalysisState, block: dict, index: int
) -> ft.Container:
    is_initial = block["type"] == "initial"
    is_failed = block.get("failed", False)
    controls: list[ft.Control] = []

    if is_initial:
        controls.append(
            ft.Row(
                [
                    ft.Icon(ft.Icons.DATASET_ROUNDED, size=16, color=theme.ACCENT),
                    ft.Text("Dataset Overview", weight="bold"),
                ],
                spacing=8,
            )
        )
    else:
        header_color = theme.ERROR if is_failed else theme.ACCENT
        controls.append(
            ft.Row(
                [
                    ft.Icon(
                        ft.Icons.ERROR_OUTLINE_ROUNDED
                        if is_failed
                        else ft.Icons.AUTO_AWESOME_ROUNDED,
                        size=14,
                        color=header_color,
                    ),
                    ft.Text(
                        block["prompt"],
                        weight="bold",
                        expand=True,
                        max_lines=2,
                        overflow="ellipsis",
                    ),
                ],
                spacing=8,
            )
        )

    if is_initial:
        describe_data = block.get("describe_data")
        import pandas as pd

        if (
            isinstance(describe_data, str) or describe_data is None
        ) and state.current_df is not None:
            try:
                describe_data = (
                    state.current_df.describe(include="all").round(2).fillna("")
                )
                block["describe_data"] = describe_data
            except Exception:
                pass

        if isinstance(describe_data, str):
            try:
                import json

                parsed = json.loads(describe_data)
                if isinstance(parsed, dict):
                    describe_data = parsed
            except Exception:
                pass

        if isinstance(describe_data, dict):
            try:
                describe_data = pd.DataFrame.from_dict(describe_data)
                block["describe_data"] = describe_data
            except Exception:
                pass

        if describe_data is not None and isinstance(describe_data, pd.DataFrame):
            try:
                desc_cols = [
                    ft.DataColumn(
                        ft.Text("Stat", size=tokens.FONT_XS, weight=ft.FontWeight.W_600)
                    )
                ] + [
                    ft.DataColumn(
                        ft.Text(
                            str(c)[:15], size=tokens.FONT_XS, weight=ft.FontWeight.W_600
                        )
                    )
                    for c in describe_data.columns[:20]
                ]
                desc_rows = []
                for stat_name in describe_data.index:
                    cells = [
                        ft.DataCell(
                            ft.Text(str(stat_name), size=tokens.FONT_XS, weight="w500")
                        )
                    ]
                    for c in describe_data.columns[:20]:
                        val = describe_data.loc[stat_name, c]
                        display = str(val) if val != "" else "—"
                        if len(display) > 12:
                            display = display[:10] + "…"
                        cells.append(ft.DataCell(ft.Text(display, size=tokens.FONT_XS)))
                    desc_rows.append(ft.DataRow(cells=cells))

                controls.append(
                    ft.Container(
                        content=ft.Column(
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
                                            size=12,
                                            weight="w600",
                                        ),
                                    ],
                                    spacing=6,
                                ),
                                ft.Container(
                                    content=ft.Row(
                                        [
                                            ft.DataTable(
                                                columns=desc_cols,
                                                rows=desc_rows,
                                                heading_row_height=34,
                                                data_row_max_height=30,
                                                column_spacing=12,
                                                border=ft.Border.all(
                                                    1,
                                                    ft.Colors.with_opacity(
                                                        0.1, ft.Colors.ON_SURFACE
                                                    ),
                                                ),
                                                border_radius=8,
                                            )
                                        ],
                                        scroll=ft.ScrollMode.AUTO,
                                    ),
                                    border_radius=8,
                                ),
                            ],
                            spacing=6,
                        ),
                        padding=ft.Padding(0, 8, 0, 8),
                    )
                )

                col_chips = []
                for c in describe_data.columns[:20]:
                    dtype_str = "?"
                    null_ct = 0
                    if state.current_df is not None and c in state.current_df.columns:
                        dtype_str = str(state.current_df[c].dtype)
                        null_ct = int(state.current_df[c].isnull().sum())

                    null_color = theme.ERROR if null_ct > 0 else theme.SUCCESS
                    col_chips.append(
                        ft.Container(
                            content=ft.Column(
                                [
                                    ft.Text(
                                        str(c)[:18],
                                        size=11,
                                        weight="w600",
                                        max_lines=1,
                                        overflow="ellipsis",
                                    ),
                                    ft.Text(
                                        dtype_str,
                                        size=10,
                                        color=ft.Colors.ON_SURFACE_VARIANT,
                                    ),
                                    ft.Text(
                                        f"{null_ct} null" if null_ct > 0 else "0 null",
                                        size=10,
                                        color=null_color,
                                    ),
                                ],
                                spacing=2,
                                horizontal_alignment="center",
                            ),
                            padding=ft.Padding(8, 6, 8, 6),
                            border_radius=8,
                            bgcolor=ft.Colors.with_opacity(0.05, ft.Colors.ON_SURFACE),
                            width=90,
                        )
                    )
                if col_chips:
                    controls.append(
                        ft.Container(
                            content=ft.Column(
                                [
                                    ft.Row(
                                        [
                                            ft.Icon(
                                                ft.Icons.VIEW_COLUMN_ROUNDED,
                                                size=14,
                                                color=theme.ACCENT,
                                            ),
                                            ft.Text(
                                                "Column Info", size=12, weight="w600"
                                            ),
                                        ],
                                        spacing=6,
                                    ),
                                    ft.Container(
                                        content=ft.Row(col_chips, spacing=6),
                                        padding=ft.Padding(0, 4, 0, 0),
                                    ),
                                ],
                                spacing=6,
                            ),
                            padding=ft.Padding(0, 4, 0, 8),
                        )
                    )
            except Exception as ex:
                logger.error("Block 0 describe render failed: %s", ex)

    if not is_initial:
        if block.get("figure_png"):
            chart_ui = build_chart_container(block)
            if chart_ui:
                controls.append(chart_ui)

        text_ui = build_text_output_container(block.get("result"), block.get("stdout"))
        if text_ui:
            controls.append(text_ui)

    desc = block.get("description", "")
    controls.append(
        ft.Container(
            content=ft.Row(
                [
                    ft.Icon(
                        ft.Icons.LIGHTBULB_OUTLINE_ROUNDED, size=16, color=theme.ACCENT
                    ),
                    ft.Text(
                        desc,
                        size=tokens.FONT_SM,
                        color=ft.Colors.ON_SURFACE_VARIANT,
                        expand=True,
                    ),
                ],
                vertical_alignment="start",
            ),
            padding=12,
            bgcolor=ft.Colors.with_opacity(0.05, theme.ACCENT),
            border_radius=8,
        )
    )

    code = block.get("code", "")
    if code:
        adv = ft.Ref[ft.Container]()

        def toggle(e, ref=adv):
            ref.current.visible = not ref.current.visible
            view_state.page.update()

        controls.append(
            ft.Container(
                content=ft.Row(
                    [
                        ft.Icon(
                            ft.Icons.KEYBOARD_ARROW_DOWN_ROUNDED,
                            size=20,
                            color=ft.Colors.ON_SURFACE_VARIANT,
                        ),
                        ft.Text(
                            "View Code", size=12, color=ft.Colors.ON_SURFACE_VARIANT
                        ),
                    ],
                    alignment="center",
                    spacing=4,
                ),
                on_click=toggle,
                ink=True,
                padding=ft.Padding(0, 4, 0, 0),
                alignment=ft.Alignment.CENTER,
            )
        )
        controls.append(
            ft.Container(
                ref=adv, content=build_terminal(view_state, code, index), visible=False
            )
        )

    if not is_initial:
        action_row = []
        if is_failed:
            action_row.append(
                ft.TextButton(
                    "Retry with AI",
                    icon=ft.Icons.REFRESH_ROUNDED,
                    on_click=lambda e, p=block["prompt"]: view_state.page.run_task(
                        on_suggestion_selected, view_state, p
                    ),
                    style=ft.ButtonStyle(color=theme.WARNING),
                    disabled=state.is_analyzing,
                )
            )
        is_pinned = any(
            any(
                b.get("source_block_id") == block.get("id") for b in r.get("blocks", [])
            )
            for r in state.user_reports
        )
        is_pinning = view_state.pinning_block_index == index
        if not is_failed:
            action_row.append(
                ft.TextButton(
                    "Pinned" if is_pinned else "Pin to Report",
                    icon=ft.Icons.PUSH_PIN_ROUNDED
                    if is_pinned
                    else ft.Icons.PUSH_PIN_OUTLINED,
                    on_click=lambda e, idx=index: on_pin_block(view_state, idx),
                    style=ft.ButtonStyle(
                        color=theme.ACCENT if is_pinned else theme.PRIMARY
                    ),
                    disabled=state.is_analyzing or is_pinning,
                )
                if not is_pinning
                else ft.TextButton(
                    content=ft.Row(
                        [
                            ft.ProgressRing(width=14, height=14, stroke_width=2),
                            ft.Text(" ", size=14),
                        ],
                        spacing=6,
                    ),
                    disabled=True,
                )
            )
        controls.append(ft.Row(action_row, alignment=ft.MainAxisAlignment.END))

    sug = block.get("suggestions", [])
    if sug:
        controls.append(
            ft.Divider(
                height=1,
                thickness=0.5,
                color=ft.Colors.with_opacity(0.1, ft.Colors.ON_SURFACE),
            )
        )
        controls.append(
            build_suggestion_chips(
                sug,
                lambda p: view_state.page.run_task(
                    on_suggestion_selected, view_state, p
                ),
                state.is_analyzing,
                page=view_state.page,
                credit_service=view_state.credit_service,
            )
        )

    return ft.Container(
        content=ft.Column(controls, spacing=10),
        padding=16,
        margin=ft.Margin(tokens.SPACE_LG, 8, tokens.SPACE_LG, 8),
        border_radius=16,
        bgcolor=theme.GLASS_BG,
        border=ft.Border.all(1, theme.GLASS_BORDER_COLOR),
    )


def build_skeleton_loader() -> ft.Container:
    """Build a premium shimmering skeleton loader card for active AI analysis."""
    skeleton_layout = ft.Column(
        [
            # Header Row Placeholder
            ft.Row(
                [
                    ft.Container(
                        width=16,
                        height=16,
                        border_radius=8,
                        bgcolor=ft.Colors.ON_SURFACE_VARIANT,
                    ),
                    ft.Container(
                        width=140,
                        height=12,
                        border_radius=4,
                        bgcolor=ft.Colors.ON_SURFACE_VARIANT,
                    ),
                ],
                spacing=8,
            ),
            # Content Area Placeholder
            ft.Container(
                content=ft.Column(
                    [
                        ft.Container(
                            height=10,
                            width=280,
                            border_radius=3,
                            bgcolor=ft.Colors.ON_SURFACE_VARIANT,
                        ),
                        ft.Container(
                            height=10,
                            width=240,
                            border_radius=3,
                            bgcolor=ft.Colors.ON_SURFACE_VARIANT,
                        ),
                        ft.Container(
                            height=10,
                            width=160,
                            border_radius=3,
                            bgcolor=ft.Colors.ON_SURFACE_VARIANT,
                        ),
                    ],
                    spacing=6,
                ),
                padding=12,
                bgcolor=ft.Colors.with_opacity(0.04, theme.PRIMARY),
                border_radius=8,
            ),
            # Footer Action Placeholders
            ft.Row(
                [
                    ft.Container(
                        width=60,
                        height=12,
                        border_radius=3,
                        bgcolor=ft.Colors.ON_SURFACE_VARIANT,
                    ),
                ],
                alignment=ft.MainAxisAlignment.END,
            ),
        ],
        spacing=12,
    )

    return ft.Container(
        content=ft.Shimmer(
            content=skeleton_layout,
            base_color=ft.Colors.with_opacity(0.06, ft.Colors.ON_SURFACE),
            highlight_color=ft.Colors.with_opacity(0.16, ft.Colors.ON_SURFACE),
            period=1200,
        ),
        padding=16,
        margin=ft.Margin(tokens.SPACE_LG, 8, tokens.SPACE_LG, 8),
        border_radius=16,
        bgcolor=theme.GLASS_BG,
        border=ft.Border.all(1, theme.GLASS_BORDER_COLOR),
    )


def build_db_import_card(view_state: AnalysisState) -> ft.Container:
    """Build a premium, glassmorphic Database Connection Card."""
    import asyncio

    url_field = ft.Ref[ft.TextField]()

    # Dialects config
    dialects = {
        "sqlite": ("SQLite", "sqlite:///C:/path/to/database.db"),
        "postgres": (
            "PostgreSQL",
            "postgresql+psycopg2://username:password@localhost:5432/dbname",
        ),
        "mysql": ("MySQL", "mysql+mysqldb://username:password@localhost:3306/dbname"),
        "mssql": (
            "SQL Server",
            "mssql+pyodbc://username:password@localhost:1433/dbname?driver=ODBC+Driver+17+for+SQL+Server",
        ),
    }

    # If empty url, pre-fill with sqlite default
    if not view_state.db_url:
        view_state.db_url = dialects["sqlite"][1]

    def _on_dialect_changed(e):
        dialect_key = e.control.value
        view_state.db_url = dialects[dialect_key][1]
        view_state.db_tables.clear()
        view_state.db_selected_table = ""
        view_state.db_test_status = ""
        view_state.rebuild()

    async def _on_test_connection(e):
        if url_field.current:
            view_state.db_url = url_field.current.value.strip()

        if not view_state.db_url:
            view_state.db_test_status = "failed: URL cannot be empty."
            view_state.rebuild()
            return

        view_state.db_test_status = "testing"
        view_state.db_tables.clear()
        view_state.db_selected_table = ""
        view_state.rebuild()

        from services.db_service import DatabaseService

        success, msg = await asyncio.to_thread(
            DatabaseService.test_connection, view_state.db_url
        )

        if success:
            view_state.db_test_status = "success"
            tables = await asyncio.to_thread(
                DatabaseService.list_tables, view_state.db_url
            )
            view_state.db_tables = tables
        else:
            view_state.db_test_status = f"failed: {msg}"

        view_state.rebuild()

    def _on_table_selected(e):
        view_state.db_selected_table = e.control.value
        view_state.rebuild()

    def _on_import(e):
        if view_state.db_url and view_state.db_selected_table:
            from views.analysis.handlers import process_db_table

            view_state.page.run_task(
                process_db_table,
                view_state,
                view_state.db_url,
                view_state.db_selected_table,
            )

    # Build Test status feedback
    status_indicator = ft.Container()
    if view_state.db_test_status == "testing":
        status_indicator = ft.Row(
            [
                ft.ProgressRing(width=14, height=14, stroke_width=2),
                ft.Text(
                    "Testing database link...",
                    size=11,
                    color=ft.Colors.ON_SURFACE_VARIANT,
                ),
            ],
            spacing=8,
        )
    elif view_state.db_test_status == "success":
        status_indicator = ft.Row(
            [
                ft.Icon(ft.Icons.CHECK_CIRCLE_ROUNDED, color=theme.SUCCESS, size=16),
                ft.Text(
                    "Connected successfully!",
                    size=11,
                    color=theme.SUCCESS,
                    weight="bold",
                ),
            ],
            spacing=8,
        )
    elif view_state.db_test_status.startswith("failed:"):
        err = view_state.db_test_status.replace("failed:", "").strip()
        status_indicator = ft.Row(
            [
                ft.Icon(ft.Icons.CANCEL_ROUNDED, color=theme.ERROR, size=16),
                ft.Text(
                    err,
                    size=11,
                    color=theme.ERROR,
                    expand=True,
                    max_lines=2,
                    overflow="ellipsis",
                ),
            ],
            spacing=8,
            expand=True,
        )

    # Dialect dropdown
    dialect_dd = ft.Dropdown(
        label="SQL Dialect",
        value=next(
            (k for k, v in dialects.items() if view_state.db_url.startswith(k)),
            "sqlite",
        ),
        options=[ft.DropdownOption(key=k, text=v[0]) for k, v in dialects.items()],
        on_select=_on_dialect_changed,
        border_radius=12,
        border_color=theme.DARK_BORDER,
        bgcolor=theme.GLASS_BG,
    )

    url_input = ft.TextField(
        ref=url_field,
        label="Database Connection URL",
        value=view_state.db_url,
        hint_text="e.g. postgresql://user:pass@host:port/dbname",
        border_radius=12,
        border_color=theme.DARK_BORDER,
        bgcolor=theme.GLASS_BG,
        focused_border_color=theme.PRIMARY,
        text_size=13,
    )

    test_btn = ft.FilledButton(
        "Test Connection",
        icon=ft.Icons.BOLT_ROUNDED,
        style=ft.ButtonStyle(
            shape=ft.RoundedRectangleBorder(radius=12),
            bgcolor=theme.PRIMARY,
        ),
        disabled=(view_state.db_test_status == "testing"),
        on_click=lambda e: view_state.page.run_task(_on_test_connection, e),
    )

    # Tables Dropdown
    table_dd = ft.Dropdown(
        label="Select Table",
        value=view_state.db_selected_table
        if view_state.db_selected_table in view_state.db_tables
        else None,
        options=[ft.DropdownOption(key=t, text=t) for t in view_state.db_tables],
        disabled=(not view_state.db_tables),
        on_select=_on_table_selected,
        border_radius=12,
        border_color=theme.DARK_BORDER,
        bgcolor=theme.GLASS_BG,
    )

    import_btn = ft.FilledButton(
        "Import Selected Table",
        icon=ft.Icons.INPUT_ROUNDED,
        style=ft.ButtonStyle(
            shape=ft.RoundedRectangleBorder(radius=12),
            bgcolor=theme.SUCCESS,
        ),
        disabled=(not view_state.db_selected_table),
        on_click=_on_import,
    )

    form = ft.Column(
        [
            ft.Row(
                [
                    ft.Icon(ft.Icons.STORAGE_ROUNDED, size=24, color=theme.ACCENT),
                    ft.Text("Connect SQL Database", size=tokens.FONT_LG, weight="bold"),
                ],
                spacing=8,
            ),
            ft.Container(height=4),
            dialect_dd,
            url_input,
            ft.Row(
                [test_btn, status_indicator],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                spacing=10,
            ),
            ft.Divider(
                height=16,
                thickness=0.5,
                color=ft.Colors.with_opacity(0.1, ft.Colors.ON_SURFACE),
            ),
            table_dd,
            ft.Row([import_btn], alignment=ft.MainAxisAlignment.END),
        ],
        spacing=12,
        horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
    )

    return ft.Container(
        content=form,
        padding=24,
        border_radius=tokens.RADIUS_XL,
        border=ft.Border.all(2, ft.Colors.with_opacity(0.2, theme.PRIMARY)),
        bgcolor=ft.Colors.with_opacity(0.03, ft.Colors.WHITE),
        animate=ft.Animation(tokens.ANIM_DEFAULT_MS, ft.AnimationCurve.EASE_OUT),
    )
