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
    """Convert state notebook cells to standard .ipynb format and save to user Downloads or chosen path."""
    if not state.notebook_cells:
        return

    ipynb = cells_to_ipynb(state.notebook_cells)
    ipynb_text = json.dumps(ipynb, indent=2)

    try:
        from core.utils import resolve_save_path

        dataset_name = (
            state.current_dataset.get("name", "") if state.current_dataset else ""
        )
        safe_name = (
            dataset_name.split(".")[0].replace(" ", "_")
            if dataset_name
            else "spaninsight_notebook"
        )
        default_name = f"{safe_name}.ipynb"

        save_path = await resolve_save_path(page, default_name)
        if not save_path:
            return  # User canceled the save dialog

        pathlib.Path(save_path).write_text(ipynb_text, encoding="utf-8")

        if page:
            show_snack(
                page,
                f"📓 Notebook saved: {os.path.basename(save_path)}",
                success=True,
                duration=4000,
            )

        # ── Interstitial Ad on Export (Mobile) ─────────────
        if page and page.platform in (ft.PagePlatform.ANDROID, ft.PagePlatform.IOS):
            try:
                from services.ad_service import AdService

                ad_service = AdService(page)
                await ad_service.show_interstitial()
            except Exception as ad_err:
                logger.warning("Export Interstitial failed: %s", ad_err)
    except Exception as e:
        logger.error("Export failed: %s", e)
        if page:
            show_snack(page, f"Export failed: {e}", error=True)
