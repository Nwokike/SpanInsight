"""Floating Action Button and overflow menu for Analysis screen."""

from __future__ import annotations

import flet as ft

from core import theme, tokens


def build_analysis_fab(
    has_session: bool = True,
    has_cells: bool = False,
    has_schema: bool = False,
    autopilot_running: bool = False,
    on_export=None,
    on_clear_all=None,
    on_autopilot=None,
    on_manage_files=None,
    on_upload_dataset=None,
    on_export_ipynb=None,
) -> ft.FloatingActionButton | None:
    """Constructs the floating action button with contextual popup menu items."""
    if not has_session:
        return None

    export_fn = on_export_ipynb or on_export

    menu_items = []
    if has_cells:
        menu_items.extend(
            [
                ft.PopupMenuItem(
                    content="Export .ipynb",
                    icon=ft.Icons.DOWNLOAD_ROUNDED,
                    on_click=export_fn,
                ),
                ft.PopupMenuItem(
                    content="Clear All Cells",
                    icon=ft.Icons.DELETE_SWEEP_ROUNDED,
                    on_click=on_clear_all,
                ),
            ]
        )
    if has_schema and not autopilot_running:
        menu_items.append(
            ft.PopupMenuItem(
                content="Run Autopilot",
                icon=ft.Icons.ROCKET_LAUNCH_ROUNDED,
                on_click=on_autopilot,
            )
        )
    if on_upload_dataset:
        menu_items.append(
            ft.PopupMenuItem(
                content="Import Dataset",
                icon=ft.Icons.ATTACH_FILE_ROUNDED,
                on_click=on_upload_dataset,
            )
        )
    menu_items.append(
        ft.PopupMenuItem(
            content="Manage Files",
            icon=ft.Icons.FOLDER_ROUNDED,
            on_click=on_manage_files,
        )
    )

    return ft.FloatingActionButton(
        content=ft.PopupMenuButton(
            items=menu_items,
            icon=ft.Icons.MORE_VERT_ROUNDED,
            icon_color=ft.Colors.WHITE,
            icon_size=tokens.ICON_MD,
        ),
        bgcolor=theme.PRIMARY,
        mini=True,
    )
