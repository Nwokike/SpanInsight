"""Project switcher dropdown/modal component for quick context switching."""

from __future__ import annotations

import flet as ft

from core import theme, tokens
from core.state import state


def build_project_switcher(
    page: ft.Page,
    project_service,
    active_project_name: str | None = None,
    on_project_selected=None,
) -> ft.Control:
    """Builds a compact header chip showing active project with a dropdown modal to switch/create projects."""
    active_name = active_project_name or state.active_project_name or "Project 1"

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
                    from core.utils import show_snack

                    show_snack(
                        page, f"Switched to {full_proj.get('name')}", success=True
                    )

        async def _create_new(_=None):
            _close()
            existing_list = await project_service.list_projects()
            name = f"Project {len(existing_list) + 1}"
            new_p = await project_service.create_project(name=name)
            state.load_project(new_p)
            if on_project_selected:
                on_project_selected(new_p)
            if page:
                page.update()

        items = []
        for p in projects:
            is_active = p.get("id") == state.active_project_id
            proj_id = p.get("id")
            items.append(
                ft.ListTile(
                    leading=ft.Icon(
                        ft.Icons.CHECK_CIRCLE_ROUNDED
                        if is_active
                        else ft.Icons.FOLDER_ROUNDED,
                        color=theme.PRIMARY
                        if is_active
                        else ft.Colors.ON_SURFACE_VARIANT,
                        size=tokens.ICON_MD,
                    ),
                    title=ft.Text(
                        p.get("name", "Untitled"),
                        size=tokens.FONT_SM,
                        weight=ft.FontWeight.W_600
                        if is_active
                        else ft.FontWeight.NORMAL,
                    ),
                    subtitle=ft.Text(
                        f"Dataset: {p.get('primary_dataset', 'None')} • {len(p.get('notebook_cells', []))} cells",
                        size=tokens.FONT_XXS,
                        color=ft.Colors.ON_SURFACE_VARIANT,
                    ),
                    trailing=ft.Icon(
                        ft.Icons.CHEVRON_RIGHT_ROUNDED, size=tokens.ICON_SM
                    ),
                    on_click=lambda _, pid=proj_id: page.run_task(_select_project, pid),
                    shape=ft.RoundedRectangleBorder(radius=tokens.RADIUS_SM),
                )
            )

        if not items:
            items.append(
                ft.Container(
                    content=ft.Text(
                        "No projects found. Tap '+' to create one.",
                        size=tokens.FONT_SM,
                        color=ft.Colors.ON_SURFACE_VARIANT,
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
                content=ft.Column(
                    items,
                    scroll=ft.ScrollMode.AUTO,
                    spacing=tokens.SPACE_XXS,
                ),
                width=tokens.DIALOG_WIDTH_SM,
                height=tokens.DIALOG_HEIGHT_SM,
            ),
            actions=[ft.TextButton("Close", on_click=_close)],
        )
        page.show_dialog(dlg)

    return ft.Container(
        content=ft.Row(
            controls=[
                ft.Icon(
                    ft.Icons.FOLDER_SHARED_ROUNDED,
                    size=tokens.ICON_XS,
                    color=theme.PRIMARY,
                ),
                ft.Text(
                    active_name,
                    size=tokens.FONT_XS,
                    weight=ft.FontWeight.W_600,
                    color=theme.PRIMARY,
                    max_lines=1,
                    overflow=ft.TextOverflow.ELLIPSIS,
                ),
                ft.Icon(
                    ft.Icons.ARROW_DROP_DOWN_ROUNDED,
                    size=tokens.ICON_SM,
                    color=theme.PRIMARY,
                ),
            ],
            spacing=tokens.SPACE_TINY,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            tight=True,
        ),
        padding=ft.Padding(
            tokens.SPACE_SM, tokens.SPACE_XS, tokens.SPACE_SM, tokens.SPACE_XS
        ),
        height=tokens.BUTTON_HEIGHT_SM,
        border_radius=tokens.RADIUS_SM,
        bgcolor=ft.Colors.with_opacity(tokens.OPACITY_MUTED, theme.PRIMARY),
        on_click=lambda e: page.run_task(_show_switcher_modal) if page else None,
        ink=True,
    )
