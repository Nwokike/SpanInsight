"""AnalysisScreen — React-like component for the analysis engine.

Uses build_analysis_controls from views.analysis.layout to return native Controls directly,
synchronously memoized, with clean FAB hoisting lifecycle.
"""

import logging

import flet as ft
from flet import Control

from state.service_ctx import ServiceCtx

logger = logging.getLogger("AnalysisScreen")


@ft.component
def AnalysisScreen() -> Control:
    """Analysis engine screen — file import, AI prompts, autopilot, charts."""
    services = ft.use_context(ServiceCtx)
    page = ft.context.page

    def _get_analysis_controls():
        if not page:
            return None, None
        from services.report_service import ReportService
        from views.analysis.layout import build_analysis_controls

        report_service = ReportService(services.storage)
        return build_analysis_controls(
            page=page,
            credit_service=services.credits,
            report_service=report_service,
        )

    controls, fab = ft.use_memo(_get_analysis_controls, [page])

    # Sync FloatingActionButton to page.views[0] if present
    def _sync_fab():
        if page and page.views and fab:
            page.views[0].floating_action_button = fab
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

    ft.use_effect(_sync_fab, [fab])

    if controls:
        return controls

    return ft.Container(
        content=ft.Column(
            [
                ft.ProgressRing(width=32, height=32, stroke_width=3),
                ft.Text("Loading analysis engine...", size=14),
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            alignment=ft.MainAxisAlignment.CENTER,
            spacing=16,
        ),
        expand=True,
        alignment=ft.Alignment.CENTER,
    )
