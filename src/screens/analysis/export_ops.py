"""Jupyter Notebook (.ipynb) export operations."""

from __future__ import annotations

import json
import logging
import os
import pathlib

import flet as ft

from core.state import state
from core.utils import show_snack
from services.ipynb_converter import cells_to_ipynb

logger = logging.getLogger("ExportOps")


async def export_ipynb_async(page: ft.Page | None):
    """Convert state notebook cells to standard .ipynb format and save to app storage."""
    if not state.notebook_cells:
        return

    ipynb = cells_to_ipynb(state.notebook_cells)
    ipynb_text = json.dumps(ipynb, indent=2)

    try:
        storage_data = os.getenv("FLET_APP_STORAGE_DATA")
        export_dir = (
            pathlib.Path(storage_data)
            if storage_data
            else pathlib.Path(".flet") / "storage" / "data"
        )
        export_dir.mkdir(parents=True, exist_ok=True)
        export_path = export_dir / "spaninsight_notebook.ipynb"
        export_path.write_text(ipynb_text, encoding="utf-8")

        if page:
            show_snack(
                page,
                "📓 Notebook exported to app storage",
                success=True,
                duration=4000,
            )
    except Exception as e:
        logger.error("Export failed: %s", e)
        if page:
            show_snack(page, f"Export failed: {e}", error=True)
