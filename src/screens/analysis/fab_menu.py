"""Floating Action Button and overflow menu for Analysis screen."""

from __future__ import annotations

import flet as ft

from core import theme


def build_analysis_fab(
    has_session: bool,
    has_cells: bool,
    has_schema: bool,
    autopilot_running: bool,
    on_export,
    on_clear_all,
    on_autopilot,
    on_manage_files,
) -> ft.FloatingActionButton | None:
    """Constructs the floating action button with contextual popup menu items."""
    if not has_session:
        return None

    menu_items = []
    if has_cells:
        menu_items.extend(
            [
                ft.PopupMenuItem(
                    content="Export .ipynb",
                    icon=ft.Icons.DOWNLOAD_ROUNDED,
                    on_click=on_export,
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
            ),
        )
    menu_items.append(
        ft.PopupMenuItem(
            content="Manage Files",
            icon=ft.Icons.FOLDER_ROUNDED,
            on_click=on_manage_files,
        ),
    )

    return ft.FloatingActionButton(
        content=ft.PopupMenuButton(
            items=menu_items,
            icon=ft.Icons.MORE_VERT_ROUNDED,
            icon_color=ft.Colors.WHITE,
            icon_size=20,
        ),
        bgcolor=theme.PRIMARY,
        mini=True,
    )
