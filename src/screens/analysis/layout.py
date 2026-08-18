"""Top bar, mode switcher, raw data dialog, and feed layout builders for Analysis."""

from __future__ import annotations

import flet as ft

from components.dataset_overview_card import build_dataset_overview_card
from components.file_import_card import build_file_import_card
from components.project_switcher import build_project_switcher
from core import theme, tokens
from core.state import state
from screens.analysis.autopilot_bar import build_autopilot_bar
from screens.analysis.cell_list import build_add_cell_row, build_cells_container
from screens.analysis.session_banner import build_session_chip


def build_mode_switch_bar(is_expert_mode: bool, set_is_expert_mode) -> ft.Container:
    """Segmented Mode Switcher (Insight vs Expert)."""
    insight_bg = theme.PRIMARY if not is_expert_mode else ft.Colors.TRANSPARENT
    insight_fg = (
        ft.Colors.WHITE if not is_expert_mode else ft.Colors.ON_SURFACE_VARIANT
    )
    expert_bg = theme.PRIMARY if is_expert_mode else ft.Colors.TRANSPARENT
    expert_fg = ft.Colors.WHITE if is_expert_mode else ft.Colors.ON_SURFACE_VARIANT

    return ft.Container(
        padding=ft.Padding(2, 2, 2, 2),
        height=30,
        border_radius=tokens.RADIUS_SM,
        bgcolor=ft.Colors.with_opacity(0.08, ft.Colors.ON_SURFACE),
        border=ft.Border.all(1, ft.Colors.with_opacity(0.12, ft.Colors.ON_SURFACE)),
        content=ft.Row(
            controls=[
                ft.Container(
                    content=ft.Row(
                        [
                            ft.Icon(
                                ft.Icons.AUTO_AWESOME_ROUNDED,
                                size=12,
                                color=insight_fg,
                            ),
                            ft.Text(
                                "Insight",
                                size=tokens.FONT_XS,
                                weight=ft.FontWeight.BOLD
                                if not is_expert_mode
                                else ft.FontWeight.NORMAL,
                                color=insight_fg,
                            ),
                        ],
                        spacing=3,
                        alignment=ft.MainAxisAlignment.CENTER,
                        tight=True,
                    ),
                    bgcolor=insight_bg,
                    border_radius=tokens.RADIUS_SM,
                    padding=ft.Padding(8, 3, 8, 3),
                    ink=True,
                    on_click=lambda _: set_is_expert_mode(False),
                ),
                ft.Container(
                    content=ft.Row(
                        [
                            ft.Icon(ft.Icons.CODE_ROUNDED, size=12, color=expert_fg),
                            ft.Text(
                                "Expert",
                                size=tokens.FONT_XS,
                                weight=ft.FontWeight.BOLD
                                if is_expert_mode
                                else ft.FontWeight.NORMAL,
                                color=expert_fg,
                            ),
                        ],
                        spacing=3,
                        alignment=ft.MainAxisAlignment.CENTER,
                        tight=True,
                    ),
                    bgcolor=expert_bg,
                    border_radius=tokens.RADIUS_SM,
                    padding=ft.Padding(8, 3, 8, 3),
                    ink=True,
                    on_click=lambda _: set_is_expert_mode(True),
                ),
            ],
            spacing=2,
            tight=True,
        ),
    )


def open_raw_data_dialog(page: ft.Page | None, schema_json: dict):
    """Open a modal DataTable previewing dataset rows."""
    if not schema_json or not page:
        return
    head_records = schema_json.get("head", [])
    if not head_records:
        from core.utils import show_snack

        show_snack(page, "No preview rows available for this dataset.")
        return

    cols = list(head_records[0].keys()) if head_records else []
    dt_cols = [
        ft.DataColumn(
            ft.Text(str(c)[:16], size=tokens.FONT_XS, weight=ft.FontWeight.W_600)
        )
        for c in cols
    ]
    dt_rows = []
    for r in head_records:
        cells = [
            ft.DataCell(
                ft.Text(
                    str(r.get(c, "—")),
                    size=tokens.FONT_XS,
                    font_family="RobotoMono",
                )
            )
            for c in cols
        ]
        dt_rows.append(ft.DataRow(cells=cells))

    dlg = ft.AlertDialog(
        title=ft.Text(
            f"Dataset Preview ({state.active_project_dataset or 'Active Dataset'})",
            size=tokens.FONT_MD,
            weight=ft.FontWeight.W_600,
        ),
        content=ft.Container(
            content=ft.Row(
                controls=[
                    ft.DataTable(
                        columns=dt_cols,
                        rows=dt_rows,
                        heading_row_height=36,
                        data_row_max_height=32,
                        column_spacing=18,
                    )
                ],
                scroll=ft.ScrollMode.AUTO,
            ),
            width=650,
            height=260,
        ),
        actions=[
            ft.TextButton("Close", on_click=lambda _: page.pop_dialog()),
        ],
    )
    page.show_dialog(dlg)


def build_analysis_top_bar(
    page: ft.Page | None,
    projects,
    active_project_name: str,
    on_project_selected,
    on_new_project,
    on_pick_file,
    schema_json: dict,
    is_expert_mode: bool,
    set_is_expert_mode,
    session_name: str,
) -> ft.Column:
    """Construct top header containing project switcher, dataset badge, mode toggle, and session chip."""
    project_chip = build_project_switcher(
        page,
        projects,
        active_project_name=active_project_name,
        on_project_selected=on_project_selected,
    )

    new_project_btn = ft.FilledButton(
        "New Project",
        icon=ft.Icons.ADD_ROUNDED,
        style=ft.ButtonStyle(
            bgcolor=ft.Colors.with_opacity(0.12, theme.PRIMARY),
            color=theme.PRIMARY,
            shape=ft.RoundedRectangleBorder(radius=tokens.RADIUS_SM),
            padding=ft.Padding(10, 4, 10, 4),
        ),
        height=30,
        on_click=lambda _: on_new_project(),
    )

    dataset_label = state.active_project_dataset or (
        schema_json.get("name") if schema_json else ""
    )
    dataset_indicator = ft.Container()
    if dataset_label:
        dataset_indicator = ft.Container(
            content=ft.Row(
                [
                    ft.Icon(
                        ft.Icons.DATASET_ROUNDED,
                        size=14,
                        color=theme.ACCENT,
                    ),
                    ft.Text(
                        dataset_label,
                        size=tokens.FONT_XS,
                        weight=ft.FontWeight.W_600,
                        color=theme.ACCENT,
                        max_lines=1,
                        overflow=ft.TextOverflow.ELLIPSIS,
                    ),
                    ft.IconButton(
                        icon=ft.Icons.REFRESH_ROUNDED,
                        icon_size=13,
                        tooltip="Change Dataset",
                        on_click=lambda _: on_pick_file(),
                        style=ft.ButtonStyle(padding=2),
                    ),
                ],
                spacing=tokens.SPACE_XXS,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                tight=True,
            ),
            padding=ft.Padding(8, 4, 8, 4),
            height=30,
            border_radius=tokens.RADIUS_SM,
            bgcolor=ft.Colors.with_opacity(0.08, theme.ACCENT),
        )

    mode_switch_bar = build_mode_switch_bar(is_expert_mode, set_is_expert_mode)
    session_chip = build_session_chip(session_name, state.session_hardware)
    autopilot_bar = build_autopilot_bar(
        is_running=state.autopilot_running,
        progress_text=state.autopilot_progress,
        on_stop=lambda _: setattr(state, "autopilot_cancelled", True),
    )

    return ft.Column(
        controls=[
            ft.Container(
                content=ft.Row(
                    controls=[
                        project_chip,
                        dataset_indicator,
                        new_project_btn,
                        mode_switch_bar,
                        session_chip,
                    ],
                    alignment=ft.MainAxisAlignment.START,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=tokens.SPACE_SM,
                    scroll=ft.ScrollMode.ADAPTIVE,
                ),
                padding=ft.Padding(
                    tokens.SPACE_MD, tokens.SPACE_SM, tokens.SPACE_MD, tokens.SPACE_XXS
                ),
            ),
            autopilot_bar,
        ],
        spacing=0,
    )


def build_analysis_feed(
    page: ft.Page | None,
    schema_json: dict,
    is_expert_mode: bool,
    suggestions: list,
    cell_refs_map,
    on_trigger_run_cell,
    on_stop_cell,
    on_delete_cell,
    on_move_cell,
    on_cell_change,
    on_clear_output,
    on_pin_block,
    on_submit_prompt,
    on_pick_file,
    is_generating: bool,
    on_add_cell,
) -> ft.ListView:
    """Build the main feed containing dataset card, cell cards, or file import placeholder."""
    has_dataset = bool(schema_json) or bool(state.notebook_cells)
    feed_controls = []

    if schema_json and not is_expert_mode:
        active_desc = schema_json.get("description", "")
        feed_controls.append(
            build_dataset_overview_card(
                dataset_name=state.active_project_dataset or "Active Dataset",
                schema=schema_json,
                page=page,
                initial_description=active_desc,
                suggestions=suggestions,
                on_suggestion_selected=lambda p: on_submit_prompt(p),
                on_view_raw_data=lambda: open_raw_data_dialog(page, schema_json),
                on_inspect_schema=lambda: __import__(
                    "components.dataset_inspector",
                    fromlist=["show_dataset_inspector"],
                ).show_dataset_inspector(
                    page,
                    state.active_project_dataset or "Active Dataset",
                    schema_json,
                ),
            )
        )

    cell_controls = build_cells_container(
        page=page,
        notebook_cells=state.notebook_cells,
        cell_refs_map=cell_refs_map,
        on_run_cell=on_trigger_run_cell,
        on_stop_cell=on_stop_cell,
        on_delete_cell=on_delete_cell,
        on_move_cell=on_move_cell,
        on_cell_change=on_cell_change,
        on_clear_output=on_clear_output,
        is_expert_mode=is_expert_mode,
        on_pin_report=on_pin_block,
        on_suggestion_selected=lambda p: on_submit_prompt(p),
    )

    if cell_controls:
        feed_controls.extend(cell_controls)

    if is_expert_mode:
        feed_controls.append(
            build_add_cell_row(
                on_add_cell=on_add_cell,
                visible=True,
            )
        )

    import_area = build_file_import_card(
        on_pick=lambda: on_pick_file(),
        is_loading=is_generating,
    )

    return ft.ListView(
        controls=feed_controls if (has_dataset and feed_controls) else [import_area],
        expand=True,
        spacing=tokens.SPACE_SM,
        padding=ft.Padding(
            tokens.SPACE_MD, tokens.SPACE_SM, tokens.SPACE_MD, tokens.SPACE_MD
        ),
        auto_scroll=True,
    )
