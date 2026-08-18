"""Reports event handlers export."""

from __future__ import annotations

from screens.reports.ai_handlers import on_ai_edit, on_voice_toggle
from screens.reports.report_ops import (
    load_reports,
    on_back,
    on_delete_report,
    on_import,
    on_open_report,
    on_save,
)
from screens.reports.sharing_ops import (
    on_share,
    on_toggle_featured,
    on_view_live,
)

__all__ = [
    "load_reports",
    "on_ai_edit",
    "on_back",
    "on_delete_report",
    "on_import",
    "on_open_report",
    "on_save",
    "on_share",
    "on_toggle_featured",
    "on_view_live",
    "on_voice_toggle",
]
