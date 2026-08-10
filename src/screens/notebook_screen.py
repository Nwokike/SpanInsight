"""NotebookScreen — React-like wrapper for the Colab notebook view.

Wraps the existing build_notebook_view which handles session management,
code execution, cell management, and file uploads.
"""

import logging

import flet as ft
from flet import Control

from state.service_ctx import ServiceCtx

logger = logging.getLogger("NotebookScreen")


@ft.component
def NotebookScreen() -> Control:
    """Colab notebook screen — code cells, execution, session management."""
    services = ft.use_context(ServiceCtx)
    page = ft.context.page

    def _get_notebook_view():
        if not page:
            return None
        from views.notebook.layout import build_notebook_view

        return build_notebook_view(
            page=page,
            colab_service=services.colab,
            credit_service=services.credits,
            storage=services.storage,
        )

    notebook_view = ft.use_memo(_get_notebook_view, [page])

    # Sync FloatingActionButton to page.views[0]
    def _sync_fab():
        if (
            page
            and page.views
            and notebook_view
            and notebook_view.floating_action_button
        ):
            page.views[0].floating_action_button = notebook_view.floating_action_button
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

    ft.use_effect(_sync_fab, [notebook_view])

    if notebook_view and notebook_view.controls:
        return ft.Column(
            controls=notebook_view.controls,
            expand=True,
            scroll=ft.ScrollMode.AUTO,
        )

    return ft.Container(
        content=ft.Column(
            [
                ft.ProgressRing(width=32, height=32, stroke_width=3),
                ft.Text("Loading notebook...", size=14),
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            alignment=ft.MainAxisAlignment.CENTER,
            spacing=16,
        ),
        expand=True,
        alignment=ft.Alignment.CENTER,
    )
