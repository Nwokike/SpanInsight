"""FilesScreen — Modular Colab filesystem explorer and transfer manager."""

from __future__ import annotations

import logging
import posixpath

import flet as ft
from flet import Control

from components.file_item import build_file_item
from core import theme, tokens
from core.state import state
from screens.files.actions import (
    do_delete_async,
    do_new_folder_async,
    handle_download_async,
    handle_load_in_analysis,
    handle_upload_async,
)
from screens.files.components import (
    build_breadcrumbs,
    build_empty_dir_view,
    build_no_session_view,
    is_data_file,
)
from state.service_ctx import ServiceCtx

logger = logging.getLogger("FilesScreen")


@ft.component
def FilesScreen() -> Control:
    """Colab file manager — upload, download, delete, browse, load in analysis."""
    services = ft.use_context(ServiceCtx)
    page = ft.context.page

    current_path, set_current_path = ft.use_state("/content")
    listing, set_listing = ft.use_state([])
    selected_files, set_selected_files = ft.use_state(set())
    is_loading, set_is_loading = ft.use_state(False)
    selection_mode, set_selection_mode = ft.use_state(False)

    active_session = state.active_session_name

    # ── No session guard ──────────────────────────────────────────
    if not active_session:
        return build_no_session_view(lambda _: setattr(state, "current_tab", 1))

    # ── Directory fetch ───────────────────────────────────────────
    async def fetch_listing(path: str):
        set_is_loading(True)
        try:
            data = await services.colab.ls(path, active_session)
            set_listing(data)
            set_selected_files(set())
        except Exception as e:
            logger.error("ls failed: %s", e)
            if page:
                from core.utils import show_snack

                show_snack(page, f"Failed: {e}", error=True)
        finally:
            set_is_loading(False)
            if page:
                page.update()

    async def _fetch_effect():
        if active_session:
            await fetch_listing(current_path)

    ft.use_effect(_fetch_effect, [current_path, active_session])

    def _clear_selection():
        set_selected_files(set())
        set_selection_mode(False)
        if page:
            page.update()

    # ── Item click ────────────────────────────────────────────────
    def on_item_click(item: dict):
        if selection_mode:
            new_sel = set(selected_files)
            name = item["name"]
            if name in new_sel:
                new_sel.remove(name)
            else:
                new_sel.add(name)
            set_selected_files(new_sel)
        else:
            if item["type"] == "directory":
                set_current_path(posixpath.join(current_path, item["name"]))
            else:
                new_sel = {item["name"]}
                set_selected_files(new_sel)
                set_selection_mode(True)

    # ── Delete dialog ─────────────────────────────────────────────
    def handle_delete():
        if not selected_files:
            return
        names = list(selected_files)
        names_str = "\n".join(f"• {n}" for n in names)

        def _close(_=None):
            dlg.open = False
            page.update()

        dlg = ft.AlertDialog(
            title=ft.Text(f"Delete {len(names)} item(s)?"),
            content=ft.Text(
                f"This cannot be undone:\n{names_str}",
                size=tokens.FONT_SM,
            ),
            actions=[
                ft.TextButton("Cancel", on_click=_close),
                ft.FilledButton(
                    "Delete",
                    style=ft.ButtonStyle(bgcolor=ft.Colors.ERROR),
                    on_click=lambda _: (
                        _close(),
                        page.run_task(
                            do_delete_async,
                            page,
                            services.colab,
                            current_path,
                            names,
                            active_session,
                            set_is_loading,
                            _clear_selection,
                            fetch_listing,
                        ),
                    ),
                ),
            ],
        )
        page.show_dialog(dlg)

    # ── New Folder dialog ─────────────────────────────────────────
    def handle_new_folder():
        def _close(_=None):
            dlg.open = False
            page.update()

        tf = ft.TextField(
            label="Folder name",
            autofocus=True,
            on_submit=lambda e: (
                _close(),
                page.run_task(
                    do_new_folder_async,
                    page,
                    services.colab,
                    current_path,
                    e.control.value or "",
                    active_session,
                    set_is_loading,
                    fetch_listing,
                ),
            ),
        )
        dlg = ft.AlertDialog(
            title=ft.Text("New Folder"),
            content=tf,
            actions=[
                ft.TextButton("Cancel", on_click=_close),
                ft.FilledButton(
                    "Create",
                    on_click=lambda _: (
                        _close(),
                        page.run_task(
                            do_new_folder_async,
                            page,
                            services.colab,
                            current_path,
                            tf.value or "",
                            active_session,
                            set_is_loading,
                            fetch_listing,
                        ),
                    ),
                ),
            ],
        )
        page.show_dialog(dlg)

    # ── Action bar ────────────────────────────────────────────────
    n_sel = len(selected_files)
    action_controls: list[ft.Control] = []

    if selection_mode and n_sel > 0:
        action_controls.append(
            ft.Container(
                content=ft.Text(
                    f"{n_sel} selected",
                    size=tokens.FONT_XS,
                    weight=ft.FontWeight.W_600,
                    color=theme.PRIMARY,
                ),
                padding=ft.Padding(tokens.SPACE_SM, 0, tokens.SPACE_SM, 0),
            )
        )

        sel_item = next((i for i in listing if i["name"] in selected_files), None)
        if n_sel == 1 and sel_item and is_data_file(sel_item["name"]):
            action_controls.append(
                ft.IconButton(
                    ft.Icons.ANALYTICS_ROUNDED,
                    tooltip="Load in Analysis",
                    icon_color=theme.PRIMARY,
                    on_click=lambda _: handle_load_in_analysis(
                        page, current_path, sel_item["name"]
                    ),
                )
            )

        action_controls.extend(
            [
                ft.IconButton(
                    ft.Icons.DOWNLOAD_ROUNDED,
                    tooltip="Download",
                    on_click=lambda _: page.run_task(
                        handle_download_async,
                        page,
                        services.colab,
                        current_path,
                        selected_files,
                        listing,
                        active_session,
                        _clear_selection,
                    ),
                ),
                ft.IconButton(
                    ft.Icons.DELETE_ROUNDED,
                    tooltip="Delete",
                    icon_color=ft.Colors.ERROR,
                    on_click=lambda _: handle_delete(),
                ),
                ft.IconButton(
                    ft.Icons.CLOSE_ROUNDED,
                    tooltip="Cancel selection",
                    on_click=lambda _: _clear_selection(),
                ),
            ]
        )
    else:
        action_controls.extend(
            [
                ft.IconButton(
                    ft.Icons.CHECKLIST_ROUNDED,
                    tooltip="Select items",
                    icon_color=theme.PRIMARY if selection_mode else None,
                    on_click=lambda _: set_selection_mode(not selection_mode),
                ),
                ft.IconButton(
                    ft.Icons.UPLOAD_FILE_ROUNDED,
                    tooltip="Upload file",
                    on_click=lambda _: page.run_task(
                        handle_upload_async,
                        page,
                        services.colab,
                        current_path,
                        active_session,
                        fetch_listing,
                    ),
                ),
                ft.IconButton(
                    ft.Icons.CREATE_NEW_FOLDER_ROUNDED,
                    tooltip="New folder",
                    on_click=lambda _: handle_new_folder(),
                ),
                ft.IconButton(
                    ft.Icons.REFRESH_ROUNDED,
                    tooltip="Refresh",
                    on_click=lambda _: page.run_task(fetch_listing, current_path),
                ),
            ]
        )

    header = ft.Container(
        content=ft.Row(
            controls=[
                ft.Container(
                    content=build_breadcrumbs(current_path, set_current_path),
                    expand=True,
                ),
                ft.Row(controls=action_controls, spacing=0),
            ],
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        padding=ft.Padding(
            tokens.SPACE_MD, tokens.SPACE_XS, tokens.SPACE_XS, tokens.SPACE_XS
        ),
    )

    # ── File list / Empty state ───────────────────────────────────
    if is_loading and not listing:
        list_content: ft.Control = ft.Container(
            content=ft.ProgressRing(),
            alignment=ft.Alignment.CENTER,
            expand=True,
        )
    elif not listing:
        list_content = build_empty_dir_view(
            lambda _: page.run_task(
                handle_upload_async,
                page,
                services.colab,
                current_path,
                active_session,
                fetch_listing,
            )
        )
    else:
        list_items = [
            build_file_item(
                file_info=item,
                selected=(item["name"] in selected_files),
                selection_mode=selection_mode,
                on_click=lambda _, i=item: on_item_click(i),
            )
            for item in listing
        ]
        list_content = ft.ListView(
            controls=list_items,
            expand=True,
            spacing=tokens.SPACE_XXS,
            padding=ft.Padding(tokens.SPACE_MD, 0, tokens.SPACE_MD, tokens.SPACE_MD),
        )

    return ft.Column(
        controls=[
            header,
            ft.ProgressBar(
                visible=is_loading,
                height=2,
                color=theme.PRIMARY,
                bgcolor=ft.Colors.TRANSPARENT,
            ),
            ft.Divider(height=1, color=ft.Colors.OUTLINE_VARIANT),
            list_content,
        ],
        expand=True,
        spacing=0,
    )
