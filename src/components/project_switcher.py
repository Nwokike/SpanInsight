"""Project switcher dropdown/modal component for quick context switching."""

from __future__ import annotations

import flet as ft

from core import theme, tokens
from core.state import state


def build_project_switcher(
    page: ft.Page, project_service, on_project_selected=None
) -> ft.Control:
    """Builds a compact header chip showing active project with a dropdown modal to switch/create projects."""
    active_name = state.active_project_name or "Default Session"

    async def _show_switcher_modal(_=None):
        if not project_service or not page:
            return

        projects = await project_service.list_projects()

        def _close(_=None):
            dlg.open = False
            page.update()

        async def _select_project(pid: str):
            _close()
            full_proj = await project_service.get_project(pid)
            if full_proj:
                state.load_project(full_proj)
                if on_project_selected:
                    on_project_selected(full_proj)
                if page:
                    page.snack_bar = ft.SnackBar(
                        ft.Text(f"Switched to {full_proj.get('name')}")
                    )
                    page.snack_bar.open = True
                    page.update()

        async def _create_new(_=None):
            _close()
            new_p = await project_service.create_project(name="New Analysis")
            state.load_project(new_p)
            state.current_tab = 1
            if on_project_selected:
                on_project_selected(new_p)
            if page:
                page.update()

        items = []
        for p in projects:
            is_active = p.get("id") == state.active_project_id
            items.append(
                ft.ListTile(
                    leading=ft.Icon(
                        ft.Icons.CHECK_CIRCLE_ROUNDED
                        if is_active
                        else ft.Icons.FOLDER_ROUNDED,
                        color=theme.PRIMARY
                        if is_active
                        else ft.Colors.ON_SURFACE_VARIANT,
                    ),
                    title=ft.Text(
                        p.get("name", "Untitled"),
                        weight=ft.FontWeight.W_600
                        if is_active
                        else ft.FontWeight.NORMAL,
                        size=tokens.FONT_SM,
                    ),
                    subtitle=ft.Text(
                        f"{p.get('primary_dataset') or 'Empty notebook'} · {p.get('cell_count', 0)} cells",
                        size=tokens.FONT_XS,
                        color=ft.Colors.ON_SURFACE_VARIANT,
                    ),
                    on_click=lambda e, pid=p["id"]: page.run_task(_select_project, pid),
                )
            )

        if not items:
            items.append(
                ft.Container(
                    content=ft.Text(
                        "No saved projects yet. Start an analysis to create one.",
                        size=tokens.FONT_SM,
                        color=ft.Colors.ON_SURFACE_VARIANT,
                        text_align=ft.TextAlign.CENTER,
                    ),
                    padding=tokens.SPACE_MD,
                )
            )

        dlg = ft.AlertDialog(
            title=ft.Row(
                [
                    ft.Text(
                        "Switch Project",
                        size=tokens.FONT_MD,
                        weight=ft.FontWeight.W_600,
                    ),
                    ft.Container(expand=True),
                    ft.IconButton(
                        ft.Icons.ADD_ROUNDED,
                        tooltip="New Project",
                        icon_color=theme.PRIMARY,
                        on_click=lambda e: page.run_task(_create_new),
                    ),
                ],
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            content=ft.Container(
                content=ft.Column(items, scroll="auto", spacing=tokens.SPACE_XXS),
                width=360,
                height=320,
            ),
            actions=[ft.TextButton("Close", on_click=_close)],
        )
        page.show_dialog(dlg)

    return ft.Container(
        content=ft.Row(
            controls=[
                ft.Icon(ft.Icons.FOLDER_SHARED_ROUNDED, size=14, color=theme.PRIMARY),
                ft.Text(
                    active_name,
                    size=tokens.FONT_XS,
                    weight=ft.FontWeight.W_600,
                    color=theme.PRIMARY,
                    max_lines=1,
                    overflow="ellipsis",
                ),
                ft.Icon(ft.Icons.ARROW_DROP_DOWN_ROUNDED, size=18, color=theme.PRIMARY),
            ],
            spacing=4,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        padding=ft.Padding(8, 4, 8, 4),
        border_radius=tokens.RADIUS_MD,
        bgcolor=ft.Colors.with_opacity(0.08, theme.PRIMARY),
        on_click=lambda e: page.run_task(_show_switcher_modal) if page else None,
        ink=True,
    )
