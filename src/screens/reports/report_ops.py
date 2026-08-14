"""CRUD, sharing, and import actions for saved Reports."""

from __future__ import annotations

import logging

import flet as ft

from core import theme
from core.state import state
from services import ai as ai_service

logger = logging.getLogger("ReportOps")


async def load_reports(page: ft.Page, ui_state, report_service):
    """Fetch saved reports list from storage."""
    ui_state.is_loading["value"] = True
    ui_state.rebuild()
    try:
        if report_service:
            loaded = await report_service.list_reports()
            ui_state.user_reports.clear()
            ui_state.user_reports.extend(loaded)
            state.user_reports = loaded
    except Exception as e:
        logger.error("Failed to load reports: %s", e)
    ui_state.is_loading["value"] = False
    ui_state.rebuild()


async def on_open_report(page: ft.Page, ui_state, report: dict, report_service):
    """Open existing report in editor and run initial AI arrangement if unarranged."""
    ui_state.active_report["data"] = report
    ui_state.editor_blocks.clear()
    ui_state.editor_blocks.extend(report.get("blocks", []))
    ui_state.draft_title["value"] = report.get("title", "")
    ui_state.draft_desc["value"] = report.get("description", "")
    ui_state.is_public["value"] = report.get("is_public", False)
    ui_state.editor_active["value"] = True

    if not report.get("is_arranged") and len(ui_state.editor_blocks) > 1:
        ui_state.is_arranging["value"] = True
        ui_state.rebuild()
        try:
            result = await ai_service.arrange_report(
                ui_state.editor_blocks,
                report.get("dataset_name", ""),
            )
            if result and "blocks" in result:
                new_blocks = []
                for ai_block in result["blocks"]:
                    orig_idx = ai_block.get("original_index", 0)
                    if 0 <= orig_idx < len(ui_state.editor_blocks):
                        b = ui_state.editor_blocks[orig_idx].copy()
                        b["prompt"] = ai_block.get("prompt", b.get("prompt", ""))
                        new_blocks.append(b)
                if len(new_blocks) == len(ui_state.editor_blocks):
                    ui_state.editor_blocks.clear()
                    ui_state.editor_blocks.extend(new_blocks)
                if result.get("title"):
                    ui_state.draft_title["value"] = result["title"]
                if result.get("description"):
                    ui_state.draft_desc["value"] = result["description"]

                if report_service:
                    await report_service.update_report(
                        report["id"],
                        {
                            "is_arranged": True,
                            "title": ui_state.draft_title["value"],
                            "description": ui_state.draft_desc["value"],
                            "blocks": ui_state.editor_blocks,
                        },
                    )
        except Exception as e:
            logger.error("AI arrange failed: %s", e)
        ui_state.is_arranging["value"] = False

    ui_state.rebuild()


async def on_save(page: ft.Page, ui_state, report_service):
    """Persist changes to the active report in local storage."""
    ui_state.is_saving["value"] = True
    if ui_state.save_btn_ref.current:
        ui_state.save_btn_ref.current.disabled = True
        ui_state.save_btn_ref.current.update()

    try:
        if report_service and ui_state.active_report["data"]:
            await report_service.update_report(
                ui_state.active_report["data"]["id"],
                {
                    "title": ui_state.draft_title["value"],
                    "description": ui_state.draft_desc["value"],
                    "blocks": list(ui_state.editor_blocks),
                    "is_arranged": True,
                    "is_public": ui_state.is_public["value"],
                },
            )
            if page:
                page.snack_bar = ft.SnackBar(
                    ft.Text("Report saved!", color=ft.Colors.WHITE),
                    bgcolor=theme.SUCCESS,
                    duration=2000,
                )
                page.snack_bar.open = True
                page.update()
    except Exception as e:
        logger.error("Save failed: %s", e)
        if page:
            page.snack_bar = ft.SnackBar(
                ft.Text(f"Save failed: {e}"),
                duration=3000,
            )
            page.snack_bar.open = True
            page.update()
    finally:
        ui_state.is_saving["value"] = False
        if ui_state.save_btn_ref.current:
            ui_state.save_btn_ref.current.disabled = False
            ui_state.save_btn_ref.current.update()


async def on_share(page: ft.Page, ui_state, report_service, ad_service):
    """Generate public web link for report and copy to clipboard."""
    if not ui_state.active_report["data"] or ui_state.is_sharing["value"]:
        return

    ui_state.is_sharing["value"] = True
    if ui_state.share_btn_ref.current:
        ui_state.share_btn_ref.current.disabled = True
        ui_state.share_btn_ref.current.update()

    try:
        if ad_service:
            await ad_service.show_interstitial()

        if report_service:
            ui_state.active_report["data"]["blocks"] = list(ui_state.editor_blocks)
            ui_state.active_report["data"]["title"] = ui_state.draft_title["value"]
            url = await report_service.share_report(
                ui_state.active_report["data"], state.user_uuid
            )
            if url:
                try:
                    await ft.Clipboard().set(url)
                except Exception:
                    pass
                if page:
                    page.snack_bar = ft.SnackBar(
                        content=ft.Row(
                            [
                                ft.Icon(
                                    ft.Icons.CHECK_CIRCLE_ROUNDED,
                                    color=theme.SUCCESS,
                                    size=20,
                                ),
                                ft.Column(
                                    [
                                        ft.Text(
                                            "Link copied!", weight=ft.FontWeight.W_600
                                        ),
                                        ft.Text(
                                            "Open in browser for PDF/PPTX export. Link expires in 7 days.",
                                            size=12,
                                            color=ft.Colors.ON_SURFACE_VARIANT,
                                        ),
                                    ],
                                    spacing=2,
                                    expand=True,
                                ),
                            ],
                            spacing=12,
                        ),
                        duration=5000,
                    )
                    page.snack_bar.open = True
            else:
                if page:
                    page.snack_bar = ft.SnackBar(
                        ft.Text("Share failed. Try again."), duration=3000
                    )
                    page.snack_bar.open = True
            if page:
                page.update()
    except Exception as e:
        logger.error("Share failed: %s", e)
    finally:
        ui_state.is_sharing["value"] = False
        if ui_state.share_btn_ref.current:
            ui_state.share_btn_ref.current.disabled = False
            ui_state.share_btn_ref.current.update()


def on_back(page: ft.Page, ui_state, report_service):
    """Navigate back from report editor to dashboard."""
    ui_state.editor_active["value"] = False
    ui_state.active_report["data"] = None
    ui_state.editor_blocks.clear()
    if page:
        page.run_task(load_reports, page, ui_state, report_service)


async def on_import(page: ft.Page, ui_state):
    """Import an executed notebook cell (and chart image) into active report."""
    cells = state.notebook_cells
    if not cells:
        if page:
            page.snack_bar = ft.SnackBar(
                ft.Text("No notebook cells available. Run an analysis first."),
                duration=3000,
            )
            page.snack_bar.open = True
            page.update()
        return

    async def on_select_block(idx):
        cell = cells[idx]
        png_b64 = ""
        for out in cell.get("outputs", []):
            otype = out.get("output_type") or out.get("type", "")
            if otype in ("execute_result", "display_data"):
                data = out.get("data", {})
                if "image/png" in data:
                    png_b64 = data["image/png"].replace("\n", "").replace("\r", "")
                    break

        new_block = {
            "prompt": cell.get("prompt", "Analysis"),
            "description": cell.get("description", ""),
            "figure_png_b64": png_b64,
            "block_type": "chart" if png_b64 else "text",
        }
        ui_state.editor_blocks.append(new_block)
        if page:
            page.pop_dialog()
        ui_state.rebuild()
        if page:
            page.snack_bar = ft.SnackBar(ft.Text("Block imported!"), duration=2000)
            page.snack_bar.open = True
            page.update()

    items = []
    for i, cell in enumerate(cells):
        if cell.get("is_running"):
            continue
        items.append(
            ft.ListTile(
                leading=ft.Icon(
                    ft.Icons.AUTO_AWESOME_ROUNDED
                    if not cell.get("failed")
                    else ft.Icons.ERROR_OUTLINE,
                    color=theme.ACCENT if not cell.get("failed") else theme.ERROR,
                ),
                title=ft.Text(
                    cell.get("prompt", "Cell")[:60],
                    max_lines=2,
                    size=13,
                ),
                subtitle=ft.Text(
                    (cell.get("description", "")[:80] + "...")
                    if cell.get("description")
                    else "",
                    size=11,
                    color=ft.Colors.ON_SURFACE_VARIANT,
                ),
                on_click=lambda e, idx=i: (
                    page.run_task(on_select_block, idx) if page else None
                ),
                disabled=cell.get("failed", False),
            )
        )

    if not items:
        items.append(
            ft.Container(
                ft.Text(
                    "No importable cells found.", color=ft.Colors.ON_SURFACE_VARIANT
                ),
                padding=20,
            )
        )

    def _close_dlg(_=None):
        if page:
            page.pop_dialog()

    dlg = ft.AlertDialog(
        title=ft.Text("Import from Notebook"),
        content=ft.Container(
            content=ft.Column(items, scroll="auto", spacing=0),
            width=400,
            height=400,
        ),
        actions=[
            ft.TextButton("Cancel", on_click=_close_dlg),
        ],
    )
    if page:
        page.show_dialog(dlg)


async def on_view_live(page: ft.Page, ui_state, report_service, ad_service):
    """Save and launch the live report URL in system browser."""
    report = ui_state.active_report["data"]
    if not report or ui_state.is_viewing_live["value"]:
        return

    ui_state.is_viewing_live["value"] = True
    if ui_state.view_live_btn_ref.current:
        ui_state.view_live_btn_ref.current.disabled = True
        ui_state.view_live_btn_ref.current.update()

    try:
        if report_service:
            await report_service.update_report(
                report["id"],
                {
                    "title": ui_state.draft_title["value"],
                    "description": ui_state.draft_desc["value"],
                    "blocks": list(ui_state.editor_blocks),
                    "is_arranged": True,
                },
            )
        if ad_service:
            await ad_service.show_interstitial()
        report["blocks"] = list(ui_state.editor_blocks)
        report["title"] = ui_state.draft_title["value"]
        url = await report_service.share_report(report, state.user_uuid)
        if url:
            ui_state.active_report["data"]["share_url"] = url
            await ft.UrlLauncher().launch_url(url)
        else:
            if page:
                page.snack_bar = ft.SnackBar(
                    ft.Text("View live failed. Try again."), duration=3000
                )
                page.snack_bar.open = True
                page.update()
    except Exception as e:
        logger.error("View live failed: %s", e)
        if page:
            page.snack_bar = ft.SnackBar(
                ft.Text(f"View live failed: {e}"), duration=3000
            )
            page.snack_bar.open = True
            page.update()
    finally:
        ui_state.is_viewing_live["value"] = False
        if ui_state.view_live_btn_ref.current:
            ui_state.view_live_btn_ref.current.disabled = False
            ui_state.view_live_btn_ref.current.update()


async def on_delete_report(page: ft.Page, ui_state, report_id: str, report_service):
    """Delete report dialog and removal."""

    def _close_dlg(_=None):
        if page:
            page.pop_dialog()

    async def _confirm_delete(_=None):
        _close_dlg()
        ui_state.is_deleting["value"] = True
        ui_state.rebuild()
        try:
            if report_service:
                await report_service.delete_report(report_id)
        finally:
            ui_state.is_deleting["value"] = False
            on_back(page, ui_state, report_service)

    confirm_dlg = ft.AlertDialog(
        title=ft.Text("Delete Report?"),
        content=ft.Container(
            content=ft.Text(
                "Are you sure you want to permanently delete this report from your device? "
                "This cannot be undone.",
                size=13,
            ),
            width=340,
        ),
        actions=[
            ft.TextButton("Cancel", on_click=_close_dlg),
            ft.FilledButton(
                "Delete",
                bgcolor=theme.ERROR,
                color=ft.Colors.WHITE,
                on_click=lambda e: page.run_task(_confirm_delete) if page else None,
            ),
        ],
    )
    if page:
        page.show_dialog(confirm_dlg)
