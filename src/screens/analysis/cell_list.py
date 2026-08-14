"""Notebook cells list and add-cell button row builder."""

from __future__ import annotations

import flet as ft

from components.notebook_cell import build_notebook_cell
from core import tokens


def build_cells_container(
    page: ft.Page,
    notebook_cells: list[dict],
    cell_refs_map,
    on_run_cell,
    on_stop_cell,
    on_delete_cell,
    on_move_cell,
    on_cell_change,
    on_clear_output,
) -> list[ft.Control]:
    """Renders all notebook cells and refs map."""
    cell_controls = []
    for cell in notebook_cells:
        cid = cell["id"]
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
                    "+ Code",
                    icon=ft.Icons.CODE_ROUNDED,
                    on_click=lambda _: on_add_cell("code"),
                    style=ft.ButtonStyle(padding=ft.Padding(12, 6, 12, 6)),
                ),
                ft.TextButton(
                    "+ Markdown",
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
