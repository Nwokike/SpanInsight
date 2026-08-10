"""FilesScreen — React-like wrapper for the Colab file manager.

Wraps the existing build_files_view which handles file browsing,
uploads, and navigation within a Colab session.
"""

import logging

import flet as ft
from flet import Control

from state import AppStateCtx
from state.service_ctx import ServiceCtx

logger = logging.getLogger("FilesScreen")


@ft.component
def FilesScreen() -> Control:
    """Colab file manager screen."""
    state = ft.use_context(AppStateCtx)
    services = ft.use_context(ServiceCtx)
    page = ft.context.page

    def _get_files_view():
        if not page:
            return None
        from views.files import build_files_view

        return build_files_view(
            page=page,
            colab_service=services.colab,
            state=state,
            session_name=state.active_session_name or "",
        )

    files_view = ft.use_memo(_get_files_view, [page, state.active_session_name])

    # Sync FloatingActionButton to page.views[0] if present
    def _sync_fab():
        if page and page.views and files_view and files_view.floating_action_button:
            page.views[0].floating_action_button = files_view.floating_action_button
            try:
                page.update()
            except Exception:
                pass

        def _cleanup():
            if page and page.views:
                page.views[0].floating_action_button = None
                try:
                    page.update()
                except Exception:
                    pass

        return _cleanup

    ft.use_effect(_sync_fab, [files_view])

    if files_view and files_view.controls:
        return ft.Column(
            controls=files_view.controls,
            expand=True,
            scroll=ft.ScrollMode.AUTO,
        )

    return ft.Container(
        content=ft.Column(
            [
                ft.ProgressRing(width=32, height=32, stroke_width=3),
                ft.Text("Loading file manager...", size=14),
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            alignment=ft.MainAxisAlignment.CENTER,
            spacing=16,
        ),
        expand=True,
        alignment=ft.Alignment.CENTER,
    )
