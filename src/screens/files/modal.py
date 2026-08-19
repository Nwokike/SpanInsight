"""Manage Files Modal Dialog - standalone Colab file browser dialog with live actions."""

from __future__ import annotations

import logging
import posixpath

import flet as ft

from components.file_item import build_file_item
from core import tokens
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
    is_data_file,
)

logger = logging.getLogger("ManageFilesModal")


def show_manage_files_modal(page: ft.Page, colab, session_name: str):
    """Opens a modal dialog for Colab file management."""
    if not page or not colab or not session_name:
        return

    current_path = "/content"
    listing: list[dict] = []
    selected_files: set[str] = set()
    is_loading = False
    selection_mode = False

    breadcrumb_container = ft.Container(expand=True)
    action_row = ft.Row(spacing=tokens.SPACE_XS)
    list_container = ft.Container(
        content=ft.ProgressRing(),
        alignment=ft.Alignment.CENTER,
        expand=True,
    )

    dlg = ft.AlertDialog(
        title=ft.Row(
            controls=[
                ft.Icon(ft.Icons.FOLDER_ROUNDED, color=ft.Colors.PRIMARY),
                ft.Text(
                    "Manage Files",
                    weight=ft.FontWeight.W_600,
                    size=tokens.FONT_LG,
                ),
            ],
            spacing=tokens.SPACE_SM,
        ),
        content=ft.Container(
            content=ft.Column(
                controls=[
                    ft.Container(
                        content=ft.Row(
                            controls=[
                                breadcrumb_container,
                                action_row,
                            ],
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                        padding=ft.Padding(
                            tokens.SPACE_SM,
                            tokens.SPACE_NONE,
                            tokens.SPACE_SM,
                            tokens.SPACE_NONE,
                        ),
                    ),
                    ft.Divider(height=tokens.DIVIDER_THICKNESS),
                    list_container,
                ],
                spacing=tokens.SPACE_XS,
                expand=True,
            ),
            width=tokens.DIALOG_WIDTH_LG,
            height=tokens.DIALOG_HEIGHT_LG,
        ),
        actions=[
            ft.TextButton(
                "Close",
                on_click=lambda _: page.pop_dialog(),
            ),
        ],
        actions_alignment=ft.MainAxisAlignment.END,
    )

    def _render():
        nonlocal selection_mode
        # Update breadcrumbs
        breadcrumb_container.content = build_breadcrumbs(
            current_path, on_navigate=_on_navigate
        )

        # Update action buttons
        n_sel = len(selected_files)
        actions: list[ft.Control] = []

        if selection_mode and n_sel > 0:
            actions.append(
                ft.Container(
                    content=ft.Text(
                        f"{n_sel} sel",
                        size=tokens.FONT_XS,
                        weight=ft.FontWeight.W_600,
                        color=ft.Colors.PRIMARY,
                    ),
                    padding=ft.Padding(
                        tokens.SPACE_XS,
                        tokens.SPACE_NONE,
                        tokens.SPACE_XS,
                        tokens.SPACE_NONE,
                    ),
                )
            )
            sel_item = next((i for i in listing if i["name"] in selected_files), None)
            if n_sel == 1 and sel_item and is_data_file(sel_item["name"]):
                actions.append(
                    ft.IconButton(
                        ft.Icons.ANALYTICS_ROUNDED,
                        tooltip="Load in Analysis",
                        icon_color=ft.Colors.PRIMARY,
                        on_click=lambda _: (
                            page.pop_dialog(),
                            handle_load_in_analysis(
                                page, current_path, sel_item["name"]
                            ),
                        ),
                    )
                )
            actions.extend(
                [
                    ft.IconButton(
                        ft.Icons.DOWNLOAD_ROUNDED,
                        tooltip="Download",
                        on_click=lambda _: page.run_task(
                            handle_download_async,
                            page,
                            colab,
                            current_path,
                            selected_files,
                            listing,
                            session_name,
                            _clear_selection,
                        ),
                    ),
                    ft.IconButton(
                        ft.Icons.DELETE_ROUNDED,
                        tooltip="Delete",
                        icon_color=ft.Colors.ERROR,
                        on_click=lambda _: _handle_delete(),
                    ),
                    ft.IconButton(
                        ft.Icons.CLOSE_ROUNDED,
                        tooltip="Cancel selection",
                        on_click=lambda _: _clear_selection(),
                    ),
                ]
            )
        else:
            actions.extend(
                [
                    ft.IconButton(
                        ft.Icons.UPLOAD_FILE_ROUNDED,
                        tooltip="Upload files",
                        on_click=lambda _: page.run_task(
                            handle_upload_async,
                            page,
                            colab,
                            current_path,
                            session_name,
                            _fetch_listing,
                        ),
                    ),
                    ft.IconButton(
                        ft.Icons.CREATE_NEW_FOLDER_ROUNDED,
                        tooltip="New folder",
                        on_click=lambda _: _handle_new_folder(),
                    ),
                    ft.IconButton(
                        ft.Icons.REFRESH_ROUNDED,
                        tooltip="Refresh",
                        on_click=lambda _: page.run_task(_fetch_listing, current_path),
                    ),
                ]
            )
        action_row.controls = actions

        # Update file list
        if is_loading and not listing:
            list_container.content = ft.Container(
                content=ft.ProgressRing(),
                alignment=ft.Alignment.CENTER,
                expand=True,
            )
        elif not listing:
            list_container.content = build_empty_dir_view(
                lambda _: page.run_task(
                    handle_upload_async,
                    page,
                    colab,
                    current_path,
                    session_name,
                    _fetch_listing,
                )
            )
        else:
            list_items = [
                build_file_item(
                    file_info=item,
                    selected=(item["name"] in selected_files),
                    selection_mode=selection_mode,
                    on_click=lambda _, i=item: _on_item_click(i),
                )
                for item in listing
            ]
            list_container.content = ft.ListView(
                controls=list_items,
                expand=True,
                spacing=tokens.SPACE_XXS,
                padding=ft.Padding(
                    tokens.SPACE_SM,
                    tokens.SPACE_NONE,
                    tokens.SPACE_SM,
                    tokens.SPACE_SM,
                ),
            )

        try:
            dlg.update()
        except Exception:
            pass

    async def _fetch_listing(path: str):
        nonlocal is_loading, listing, current_path
        current_path = path
        is_loading = True
        _render()
        try:
            listing = await colab.ls(path, session_name)
            selected_files.clear()
        except Exception as e:
            logger.error("ls failed: %s", e)
            if page:
                from core.utils import show_snack

                show_snack(page, f"Failed: {e}", error=True)
        finally:
            is_loading = False
            _render()

    def _on_navigate(path: str):
        page.run_task(_fetch_listing, path)

    def _clear_selection():
        nonlocal selection_mode
        selected_files.clear()
        selection_mode = False
        _render()

    def _on_item_click(item: dict):
        nonlocal current_path, selection_mode
        if selection_mode:
            name = item["name"]
            if name in selected_files:
                selected_files.remove(name)
                if not selected_files:
                    selection_mode = False
            else:
                selected_files.add(name)
            _render()
        else:
            if item.get("type") == "directory":
                new_path = posixpath.normpath(
                    posixpath.join(current_path, item["name"])
                )
                page.run_task(_fetch_listing, new_path)
            else:
                selected_files.clear()
                selected_files.add(item["name"])
                selection_mode = True
                _render()

    def _handle_delete():
        if not selected_files:
            return
        names = list(selected_files)
        names_str = "\\n".join(f"• {n}" for n in names)

        del_dlg = ft.AlertDialog(
            title=ft.Text(f"Delete {len(names)} item(s)?"),
            content=ft.Text(
                f"This cannot be undone:\\n{names_str}",
                size=tokens.FONT_SM,
            ),
            actions=[
                ft.TextButton("Cancel", on_click=lambda _: page.pop_dialog()),
                ft.FilledButton(
                    "Delete",
                    style=ft.ButtonStyle(bgcolor=ft.Colors.ERROR),
                    on_click=lambda _: (
                        page.pop_dialog(),
                        page.run_task(
                            do_delete_async,
                            page,
                            colab,
                            current_path,
                            names,
                            session_name,
                            lambda _: None,
                            _clear_selection,
                            _fetch_listing,
                        ),
                    ),
                ),
            ],
        )
        page.show_dialog(del_dlg)

    def _handle_new_folder():
        tf = ft.TextField(label="Folder name", autofocus=True)
        folder_dlg = ft.AlertDialog(
            title=ft.Text("New Folder"),
            content=tf,
            actions=[
                ft.TextButton("Cancel", on_click=lambda _: page.pop_dialog()),
                ft.FilledButton(
                    "Create",
                    on_click=lambda _: (
                        page.pop_dialog(),
                        page.run_task(
                            do_new_folder_async,
                            page,
                            colab,
                            current_path,
                            tf.value or "",
                            session_name,
                            lambda _: None,
                            _fetch_listing,
                        ),
                    ),
                ),
            ],
        )
        page.show_dialog(folder_dlg)

    page.show_dialog(dlg)
    page.run_task(_fetch_listing, current_path)
