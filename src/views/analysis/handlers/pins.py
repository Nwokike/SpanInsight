import base64
import logging

import flet as ft

from core import theme, utils
from core.state import state
from core.utils import sanitize_numpy as _sanitize_numpy

logger = logging.getLogger(__name__)


def serialize_result_for_report(result_val) -> dict | None:
    """Recursively convert pandas, numpy, and python collections to serializable JSON-friendly dictionary."""
    import math

    import numpy as np
    import pandas as pd

    if result_val is None:
        return None

    # Handle DataFrame
    if isinstance(result_val, pd.DataFrame):
        return {
            "type": "dataframe",
            "columns": list(result_val.columns),
            "data": [
                [None if pd.isna(x) else x for x in row]
                for row in result_val.head(50).values.tolist()
            ],
            "total_rows": len(result_val),
        }

    # Handle Series
    if isinstance(result_val, pd.Series):
        return {
            "type": "series",
            "name": str(result_val.name) if result_val.name else "Value",
            "index": list(result_val.index),
            "data": [
                None if pd.isna(x) else x for x in result_val.head(50).values.tolist()
            ],
            "total_rows": len(result_val),
        }

    # Handle Numpy array
    if isinstance(result_val, np.ndarray):
        return {"type": "ndarray", "data": _sanitize_numpy(result_val.tolist())}

    # Handle Numpy scalar types
    if isinstance(result_val, (np.integer, np.floating, np.bool_)):
        val = result_val.item()
        if isinstance(val, float) and (math.isnan(val) or math.isinf(val)):
            return None
        return val

    # Handle standard dictionary
    if isinstance(result_val, dict):
        return {
            "type": "dict",
            "data": {
                str(k): serialize_result_for_report(v) for k, v in result_val.items()
            },
        }

    # Handle standard list/tuple
    if isinstance(result_val, (list, tuple)):
        # Check if list of dicts (potential DataFrame)
        if len(result_val) > 0 and all(isinstance(x, dict) for x in result_val):
            try:
                df = pd.DataFrame(result_val)
                return serialize_result_for_report(df)
            except Exception:
                pass
        return {
            "type": "list",
            "data": [serialize_result_for_report(v) for v in result_val],
        }

    # Handle basic types
    if isinstance(result_val, (int, float, str, bool)):
        if isinstance(result_val, float) and (
            math.isnan(result_val) or math.isinf(result_val)
        ):
            return None
        return result_val

    # Fallback to string
    return str(result_val)


def on_pin_block(view_state, index: int):
    if index < 0 or index >= len(state.analysis_blocks):
        return
    block = state.analysis_blocks[index]

    # Calculate reports where this block is currently pinned
    reports_containing_block = []
    for r in state.user_reports:
        for b in r.get("blocks", []):
            if b.get("source_block_id") == block.get("id"):
                reports_containing_block.append(r)
                break

    is_currently_pinned = len(reports_containing_block) > 0

    view_state.pinning_block_index = index
    view_state.rebuild()

    async def _pin_to_report(report_id=None):
        png_b64 = ""
        if block.get("figure_png"):
            png_b64 = base64.b64encode(block["figure_png"]).decode("utf-8")

        report_block = {
            "source_block_id": block.get("id"),
            "prompt": block.get("prompt", "Data Overview"),
            "description": block.get("description", ""),
            "figure_png_b64": png_b64,
            "block_type": "chart" if png_b64 else "text",
            "serialized_result": serialize_result_for_report(block.get("result")),
            "stdout": block.get("stdout", ""),
        }

        block["pinned"] = True
        state.charts.append(
            {
                "prompt": block.get("prompt", "Data Overview"),
                "figure": None,
                "figure_png": block.get("figure_png"),
                "description": block.get("description", ""),
            }
        )

        if not view_state.report_service:
            view_state.page.snack_bar = ft.SnackBar(
                ft.Text("Report service unavailable"), duration=2000
            )
            view_state.page.snack_bar.open = True
            view_state.page.update()
            return

        svc = view_state.report_service

        if report_id:
            await svc.add_block_to_report(report_id, report_block)
            view_state.page.snack_bar = ft.SnackBar(
                ft.Text("📌 Added to report!"), duration=2000
            )
        else:
            title = f"{state.current_df_name or 'Analysis'} Report"
            await svc.create_report(title, state.current_df_name or "", [report_block])
            view_state.page.snack_bar = ft.SnackBar(
                ft.Text("📌 New report created!"), duration=2000
            )

        view_state.page.snack_bar.open = True
        view_state.pinning_block_index = -1
        view_state.rebuild()

    async def _unpin_from_report(report_id):
        if not view_state.report_service:
            return
        svc = view_state.report_service
        report = await svc.get_report(report_id)
        if report:
            updated_blocks = [
                b
                for b in report.get("blocks", [])
                if b.get("source_block_id") != block.get("id")
            ]
            await svc.update_report(report_id, {"blocks": updated_blocks})
            view_state.page.snack_bar = ft.SnackBar(
                ft.Text(f"📌 Removed from report: {report.get('title', 'Untitled')!r}"),
                duration=2000,
            )
            view_state.page.snack_bar.open = True
        view_state.pinning_block_index = -1
        view_state.rebuild()

    async def _show_pin_picker():
        if not view_state.report_service:
            await _pin_to_report(None)
            return

        svc = view_state.report_service
        reports = await svc.list_reports()

        # Filter out reports where it is already pinned
        already_pinned_ids = {r["id"] for r in reports_containing_block}
        eligible_reports = [r for r in reports if r["id"] not in already_pinned_ids]

        if not eligible_reports:
            await _pin_to_report(None)
            return

        def _close_dlg(e=None):
            view_state.page.pop_dialog()

        def _select(rid):
            _close_dlg()
            view_state.page.run_task(_pin_to_report, rid)

        def _create_new():
            _close_dlg()
            view_state.page.run_task(_pin_to_report, None)

        items = []
        for r in eligible_reports:
            bc = len(r.get("blocks", []))
            items.append(
                ft.ListTile(
                    leading=ft.Icon(ft.Icons.ASSESSMENT_ROUNDED, color=theme.PRIMARY),
                    title=ft.Text(r.get("title", "Untitled"), size=14),
                    subtitle=ft.Text(f"{bc} block{'s' if bc != 1 else ''}", size=11),
                    on_click=lambda e, rid=r["id"]: _select(rid),
                )
            )

        items.append(
            ft.ListTile(
                leading=ft.Icon(ft.Icons.ADD_ROUNDED, color=theme.ACCENT),
                title=ft.Text(
                    "Create New Report", size=14, weight="w600", color=theme.ACCENT
                ),
                on_click=lambda e: _create_new(),
            )
        )

        if view_state.page.platform in (ft.PagePlatform.ANDROID, ft.PagePlatform.IOS):
            items.append(
                ft.Container(
                    content=ft.Column(
                        [
                            ft.Text(
                                "SPONSORED",
                                size=8,
                                weight=ft.FontWeight.W_700,
                                color=ft.Colors.ON_SURFACE_VARIANT,
                                style=ft.TextStyle(letter_spacing=1),
                            ),
                            utils.get_banner_ad(
                                unit_id="ca-app-pub-5679949845754640/5628404223",
                                width=320,
                                height=50,
                            ),
                        ],
                        horizontal_alignment="center",
                        spacing=4,
                    ),
                    alignment=ft.Alignment.CENTER,
                    padding=8,
                    border_radius=8,
                    bgcolor=theme.GLASS_BG,
                    border=ft.Border.all(1, theme.GLASS_BORDER_COLOR),
                    margin=ft.Margin(0, 10, 0, 10),
                )
            )

        dlg = ft.AlertDialog(
            title=ft.Text("Pin to Report"),
            content=ft.Container(
                content=ft.Column(items, scroll="auto", spacing=0),
                width=350,
                height=min(len(items) * 65 + 30, 350),
            ),
            actions=[ft.TextButton("Cancel", on_click=_close_dlg)],
        )

        view_state.page.show_dialog(dlg)

    async def _show_manage_dialog():
        def _close_dlg(e=None):
            view_state.page.pop_dialog()

        def _delete(rid):
            _close_dlg()
            view_state.page.run_task(_unpin_from_report, rid)

        def _pin_new():
            _close_dlg()
            view_state.page.run_task(_show_pin_picker)

        items = []
        for r in reports_containing_block:
            items.append(
                ft.ListTile(
                    leading=ft.Icon(ft.Icons.ASSESSMENT_ROUNDED, color=theme.PRIMARY),
                    title=ft.Text(r.get("title", "Untitled"), size=14),
                    subtitle=ft.Text("Click trash to unpin", size=11),
                    trailing=ft.IconButton(
                        ft.Icons.DELETE_OUTLINE_ROUNDED,
                        icon_color=theme.ERROR,
                        icon_size=18,
                        on_click=lambda e, rid=r["id"]: _delete(rid),
                    ),
                )
            )

        items.append(
            ft.ListTile(
                leading=ft.Icon(ft.Icons.ADD_ROUNDED, color=theme.ACCENT),
                title=ft.Text(
                    "Pin to Another Report", size=14, weight="w600", color=theme.ACCENT
                ),
                on_click=lambda e: _pin_new(),
            )
        )

        if view_state.page.platform in (ft.PagePlatform.ANDROID, ft.PagePlatform.IOS):
            items.append(
                ft.Container(
                    content=ft.Column(
                        [
                            ft.Text(
                                "SPONSORED",
                                size=8,
                                weight=ft.FontWeight.W_700,
                                color=ft.Colors.ON_SURFACE_VARIANT,
                                style=ft.TextStyle(letter_spacing=1),
                            ),
                            utils.get_banner_ad(
                                unit_id="ca-app-pub-5679949845754640/5628404223",
                                width=320,
                                height=50,
                            ),
                        ],
                        horizontal_alignment="center",
                        spacing=4,
                    ),
                    alignment=ft.Alignment.CENTER,
                    padding=8,
                    border_radius=8,
                    bgcolor=theme.GLASS_BG,
                    border=ft.Border.all(1, theme.GLASS_BORDER_COLOR),
                    margin=ft.Margin(0, 10, 0, 10),
                )
            )

        dlg = ft.AlertDialog(
            title=ft.Text("Manage Pinned Block"),
            content=ft.Container(
                content=ft.Column(items, scroll="auto", spacing=0),
                width=350,
                height=min(len(items) * 65 + 30, 350),
            ),
            actions=[ft.TextButton("Cancel", on_click=_close_dlg)],
        )

        view_state.page.show_dialog(dlg)

    if is_currently_pinned:
        view_state.page.run_task(_show_manage_dialog)
    else:
        view_state.page.run_task(_show_pin_picker)
