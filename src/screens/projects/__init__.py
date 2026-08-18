"""ProjectsScreen — full-screen projects management with live search, deletion, and centered header."""

from __future__ import annotations

import datetime
import logging

import flet as ft

from core import theme, tokens
from state import AppStateCtx
from state.controller_ctx import ControllerMethodsCtx
from state.service_ctx import ServiceCtx

logger = logging.getLogger("ProjectsScreen")


@ft.component
def ProjectsScreen() -> ft.Control:
    """Full-screen projects catalog with centered header, live search, and deletion."""
    state = ft.use_context(AppStateCtx)
    services = ft.use_context(ServiceCtx)
    controller = ft.use_context(ControllerMethodsCtx)
    page = ft.context.page

    projects, set_projects = ft.use_state([])
    search_query, set_search_query = ft.use_state("")
    is_loading, set_is_loading = ft.use_state(False)

    async def _fetch_projects():
        if services.projects:
            set_is_loading(True)
            try:
                loaded = await services.projects.list_projects()
                set_projects(loaded)
                state.projects_list = loaded
            except Exception as err:
                logger.error("Failed to load projects: %s", err)
            finally:
                set_is_loading(False)

    ft.use_effect(lambda: page.run_task(_fetch_projects), [state.active_project_id])

    async def _on_open_project(p: dict):
        if services.projects:
            full_proj = await services.projects.get_project(p["id"])
            if full_proj:
                state.load_project(full_proj)
                controller.close_projects_screen()
                controller.navigate_tab(1)

    async def _on_create_new(_=None):
        if services.projects:
            existing = await services.projects.list_projects()
            name = f"Project {len(existing) + 1}"
            new_p = await services.projects.create_project(name=name)
            state.load_project(new_p)
            controller.close_projects_screen()
            controller.navigate_tab(1)

    def _show_delete_dialog(p: dict):
        pname = p.get("name", "Untitled Project")
        pid = p.get("id", "")

        def _confirm_delete(_):
            async def _delete_task():
                page.pop_dialog()
                try:
                    if services.projects:
                        await services.projects.delete_project(pid)
                    if state.active_project_id == pid:
                        # Reset active project if current one was deleted
                        existing = await services.projects.list_projects()
                        if existing:
                            full = await services.projects.get_project(
                                existing[0]["id"]
                            )
                            if full:
                                state.load_project(full)
                        else:
                            new_p = await services.projects.create_project(
                                name="Project 1"
                            )
                            state.load_project(new_p)
                    await _fetch_projects()
                    from core.utils import show_snack

                    show_snack(page, f"🗑️ Project '{pname}' deleted")
                except Exception as ex:
                    logger.error("Delete project failed: %s", ex)

            page.run_task(_delete_task)

        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Row(
                [
                    ft.Icon(ft.Icons.DELETE_FOREVER_ROUNDED, color=theme.ERROR),
                    ft.Text("Delete Project", weight=ft.FontWeight.BOLD),
                ],
                spacing=tokens.SPACE_XS,
            ),
            content=ft.Text(
                f"Are you sure you want to delete '{pname}'?\n"
                "All notebook cells and local cache for this project will be permanently removed.",
                size=tokens.FONT_SM,
            ),
            actions=[
                ft.TextButton("Cancel", on_click=lambda _: page.pop_dialog()),
                ft.FilledButton(
                    "Delete",
                    style=ft.ButtonStyle(
                        bgcolor=theme.ERROR,
                        color=ft.Colors.WHITE,
                    ),
                    on_click=_confirm_delete,
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        page.show_dialog(dialog)

    # Filter projects based on search query
    q = search_query.strip().lower()
    filtered_projects = [
        p
        for p in projects
        if not q
        or q in p.get("name", "").lower()
        or q in (p.get("primary_dataset") or "").lower()
    ]

    # ── Top Bar Header: Left Back, Center Title, Right New Project ─────────
    top_header = ft.Container(
        content=ft.Row(
            controls=[
                ft.IconButton(
                    icon=ft.Icons.ARROW_BACK_ROUNDED,
                    tooltip="Back to Dashboard",
                    on_click=lambda _: controller.close_projects_screen(),
                ),
                ft.Container(
                    content=ft.Text(
                        "Projects",
                        size=tokens.FONT_LG,
                        weight=ft.FontWeight.BOLD,
                        text_align=ft.TextAlign.CENTER,
                    ),
                    expand=True,
                    alignment=ft.Alignment.CENTER,
                ),
                ft.TextButton(
                    "New Project",
                    icon=ft.Icons.ADD_ROUNDED,
                    style=ft.ButtonStyle(color=theme.PRIMARY),
                    on_click=_on_create_new,
                ),
            ],
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        padding=ft.Padding(
            tokens.SPACE_SM, tokens.SPACE_XS, tokens.SPACE_SM, tokens.SPACE_XS
        ),
        bgcolor=ft.Colors.SURFACE,
    )

    # ── Search Bar ───────────────────────────────────────────────
    search_bar = ft.Container(
        content=ft.TextField(
            hint_text="Search projects or datasets...",
            prefix_icon=ft.Icons.SEARCH_ROUNDED,
            text_size=tokens.FONT_SM,
            dense=True,
            border_radius=tokens.RADIUS_MD,
            border_color=ft.Colors.with_opacity(0.15, ft.Colors.ON_SURFACE),
            on_change=lambda e: set_search_query(e.control.value or ""),
        ),
        padding=ft.Padding(
            tokens.SPACE_LG, tokens.SPACE_SM, tokens.SPACE_LG, tokens.SPACE_XS
        ),
    )

    # ── Project Cards List ───────────────────────────────────────
    cards = []
    if is_loading:
        cards.append(
            ft.Container(
                content=ft.Row(
                    [
                        ft.ProgressRing(width=20, height=20, stroke_width=2),
                        ft.Text("Loading projects...", size=tokens.FONT_SM),
                    ],
                    spacing=tokens.SPACE_MD,
                    alignment=ft.MainAxisAlignment.CENTER,
                ),
                padding=tokens.SPACE_XL,
                alignment=ft.Alignment.CENTER,
            )
        )
    elif not filtered_projects:
        empty_msg = (
            "No projects match your search query."
            if search_query
            else "No saved projects yet. Create a new project to get started."
        )
        cards.append(
            ft.Container(
                content=ft.Column(
                    [
                        ft.Icon(
                            ft.Icons.FOLDER_OPEN_ROUNDED,
                            size=48,
                            color=ft.Colors.ON_SURFACE_VARIANT,
                        ),
                        ft.Text(
                            empty_msg,
                            size=tokens.FONT_SM,
                            color=ft.Colors.ON_SURFACE_VARIANT,
                            text_align=ft.TextAlign.CENTER,
                        ),
                    ],
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=tokens.SPACE_SM,
                ),
                padding=tokens.SPACE_XL,
                alignment=ft.Alignment.CENTER,
            )
        )
    else:
        for p in filtered_projects:
            updated_at = p.get("updated_at", 0)
            try:
                dt = datetime.datetime.fromtimestamp(updated_at, tz=datetime.UTC)
                time_str = dt.strftime("%b %d, %Y")
            except Exception:
                time_str = ""

            p_card = ft.Container(
                content=ft.Row(
                    controls=[
                        ft.Container(
                            content=ft.Icon(
                                ft.Icons.ANALYTICS_ROUNDED,
                                size=24,
                                color=theme.PRIMARY,
                            ),
                            width=44,
                            height=44,
                            border_radius=tokens.RADIUS_MD,
                            bgcolor=ft.Colors.with_opacity(0.1, theme.PRIMARY),
                            alignment=ft.Alignment.CENTER,
                        ),
                        ft.Column(
                            controls=[
                                ft.Text(
                                    p.get("name", "Untitled Project"),
                                    size=tokens.FONT_SM,
                                    weight=ft.FontWeight.W_600,
                                    max_lines=1,
                                    overflow="ellipsis",
                                ),
                                ft.Text(
                                    f"{p.get('primary_dataset') or 'Empty notebook'} · {p.get('cell_count', 0)} cells · {time_str}",
                                    size=tokens.FONT_XS,
                                    color=ft.Colors.ON_SURFACE_VARIANT,
                                    max_lines=1,
                                    overflow="ellipsis",
                                ),
                            ],
                            spacing=2,
                            expand=True,
                        ),
                        ft.Container(
                            content=ft.Text(
                                p.get("hardware", "CPU"),
                                size=tokens.FONT_XXS,
                                weight=ft.FontWeight.W_600,
                                color=theme.PRIMARY,
                            ),
                            padding=ft.Padding(6, 2, 6, 2),
                            border_radius=tokens.RADIUS_SM,
                            bgcolor=ft.Colors.with_opacity(0.1, theme.PRIMARY),
                        ),
                        ft.IconButton(
                            icon=ft.Icons.DELETE_OUTLINE_ROUNDED,
                            icon_size=18,
                            icon_color=theme.ERROR,
                            tooltip="Delete Project",
                            on_click=lambda _, proj=p: _show_delete_dialog(proj),
                            style=ft.ButtonStyle(padding=2),
                        ),
                    ],
                    spacing=tokens.SPACE_MD,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                padding=tokens.SPACE_MD,
                border_radius=tokens.RADIUS_LG,
                bgcolor=theme.GLASS_BG,
                border=ft.Border.all(1, theme.GLASS_BORDER_COLOR),
                on_click=lambda _, proj=p: page.run_task(_on_open_project, proj),
                ink=True,
            )
            cards.append(p_card)
            cards.append(ft.Container(height=tokens.SPACE_XS))

    list_container = ft.Container(
        content=ft.ListView(
            controls=cards,
            spacing=0,
            expand=True,
        ),
        padding=ft.Padding(tokens.SPACE_LG, 0, tokens.SPACE_LG, tokens.SPACE_MD),
        expand=True,
    )

    return ft.Column(
        controls=[
            top_header,
            search_bar,
            list_container,
        ],
        expand=True,
        spacing=0,
    )
