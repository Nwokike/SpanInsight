"""Notebook cells list and add-cell button row builder."""

from __future__ import annotations

from collections.abc import Callable

import flet as ft

from components.insight_card import build_insight_card
from components.notebook_cell import build_notebook_cell
from core import tokens


def build_cells_container(
    page: ft.Page,
    notebook_cells: list[dict],
    cell_refs_map,
    on_run_cell: Callable[[str], None],
    on_stop_cell: Callable[[str], None],
    on_delete_cell: Callable[[str], None],
    on_move_cell: Callable[[str, int], None],
    on_cell_change: Callable[[], None],
    on_clear_output: Callable[[str], None],
    is_expert_mode: bool = False,
    on_pin_report: Callable[[dict], None] | None = None,
    on_suggestion_selected: Callable[[str], None] | None = None,
) -> list[ft.Control]:
    """Renders cells either as SpanInsight InsightCards or Expert NotebookCells."""
    cell_controls = []
    for idx, cell in enumerate(notebook_cells):
        cid = cell["id"]
        if not is_expert_mode:
            # Skip initial dataset loading cell in Insight Mode (represented cleanly by DatasetOverviewCard)
            if cell.get("is_initial_load"):
                continue
            # SpanInsight Default: Rich Insight Card
            card = build_insight_card(
                block=cell,
                index=idx,
                page=page,
                on_run_code=lambda code, _cid=cid: on_run_cell(_cid),
                on_pin_report=on_pin_report,
                on_suggestion_selected=on_suggestion_selected,
                on_retry_ai=lambda p, _cid=cid: on_run_cell(_cid),
                on_change=on_cell_change,
            )
            cell_controls.append(card)
        else:
            # Expert Mode: Raw Jupyter/Colab Cell
            container, refs = build_notebook_cell(
                page=page,
                cell=cell,
                on_run=lambda _cid=cid: on_run_cell(_cid),
                on_stop=lambda _cid=cid: on_stop_cell(_cid),
                on_delete=lambda _cid=cid: on_delete_cell(_cid),
                on_move_up=lambda _cid=cid: on_move_cell(_cid, -1),
                on_move_down=lambda _cid=cid: on_move_cell(_cid, 1),
                on_change=on_cell_change,
                on_clear_output=lambda _cid=cid: on_clear_output(_cid),
            )
            cell_refs_map.current[cid] = refs
            cell_controls.append(container)
    return cell_controls


def build_add_cell_row(on_add_cell, visible: bool) -> ft.Container:
    """Bottom button bar to add Code or Markdown cells."""
    return ft.Container(
        content=ft.Row(
            controls=[
                ft.TextButton(
                    "Code",
                    icon=ft.Icons.CODE_ROUNDED,
                    on_click=lambda _: on_add_cell("code"),
                    style=ft.ButtonStyle(padding=ft.Padding(12, 6, 12, 6)),
                ),
                ft.TextButton(
                    "Markdown",
                    icon=ft.Icons.TEXT_FIELDS_ROUNDED,
                    on_click=lambda _: on_add_cell("markdown"),
                    style=ft.ButtonStyle(padding=ft.Padding(12, 6, 12, 6)),
                ),
            ],
            alignment=ft.MainAxisAlignment.CENTER,
            spacing=tokens.SPACE_MD,
        ),
        padding=ft.Padding(0, tokens.SPACE_SM, 0, tokens.SPACE_SM),
        visible=visible,
    )
