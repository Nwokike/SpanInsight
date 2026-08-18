"""Public sharing, live viewing, and real-time public/featured toggle for Reports."""

from __future__ import annotations

import logging

import flet as ft

from core import tokens
from core.state import state
from core.utils import show_snack

logger = logging.getLogger("ReportOps.Sharing")


async def on_share(page: ft.Page, ui_state, report_service, ad_service):
    """Generate public web link for report and copy to clipboard."""
    if not ui_state.active_report["data"] or ui_state.is_sharing["value"]:
        return

    ui_state.is_sharing["value"] = True
    ui_state.rebuild()

    try:
        if ad_service:
            await ad_service.show_interstitial()
        report = ui_state.active_report["data"]
        report["blocks"] = list(ui_state.editor_blocks)
        report["title"] = ui_state.draft_title["value"]
        report["description"] = ui_state.draft_desc["value"]
        report["is_arranged"] = True
        report["is_public"] = ui_state.is_public["value"]
        url = await report_service.share_report(report, state.user_uuid)
        if page:
            if url:
                try:
                    await page.set_clipboard_async(url)
                except Exception:
                    pass
                show_snack(
                    page,
                    "Link copied to clipboard! (Expires in 7 days)",
                    success=True,
                    duration=tokens.SNACK_DURATION_EXTENDED_MS,
                )
            else:
                show_snack(
                    page,
                    "Share failed. Try again.",
                    error=True,
                    duration=tokens.SNACK_DURATION_MD_MS,
                )
    except Exception as e:
        logger.error("Share failed: %s", e)
    finally:
        ui_state.is_sharing["value"] = False
        ui_state.rebuild()


async def on_view_live(page: ft.Page, ui_state, report_service, ad_service):
    """Save and launch the live report URL in system browser."""
    report = ui_state.active_report["data"]
    if not report or ui_state.is_viewing_live["value"]:
        return

    ui_state.is_viewing_live["value"] = True
    ui_state.rebuild()

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
                show_snack(
                    page,
                    "View live failed. Try again.",
                    error=True,
                    duration=tokens.SNACK_DURATION_MD_MS,
                )
    except Exception as e:
        logger.error("View live failed: %s", e)
        if page:
            show_snack(
                page,
                f"View live failed: {e}",
                error=True,
                duration=tokens.SNACK_DURATION_MD_MS,
            )
    finally:
        ui_state.is_viewing_live["value"] = False
        ui_state.rebuild()


async def on_toggle_featured(
    page: ft.Page, ui_state, report_service, is_featured: bool
):
    """Real-time handler when user flips 'Feature on spaninsight.com' toggle."""
    report = ui_state.active_report["data"]
    if not report:
        return

    ui_state.is_public["value"] = is_featured
    ui_state.rebuild()

    if is_featured:
        if page:
            show_snack(
                page,
                "Publishing to spaninsight.com...",
                duration=tokens.SNACK_DURATION_SHORT_MS,
            )
        report["blocks"] = list(ui_state.editor_blocks)
        report["title"] = ui_state.draft_title["value"]
        report["description"] = ui_state.draft_desc["value"]
        report["is_arranged"] = True
        report["is_public"] = True

        share_url = await report_service.share_report(report, state.user_uuid)
        if share_url:
            report["share_url"] = share_url
            if page:
                show_snack(
                    page,
                    "Featured on spaninsight.com! Live in community gallery.",
                    success=True,
                    duration=tokens.SNACK_DURATION_LONG_MS,
                )
        else:
            ui_state.is_public["value"] = False
            ui_state.rebuild()
            if page:
                show_snack(
                    page,
                    "Failed to feature report. Please check connection.",
                    error=True,
                )
    else:
        # User toggled OFF: delete from public gallery
        share_id = report.get("share_id", "")
        if page:
            show_snack(
                page,
                "Removing from spaninsight.com...",
                duration=tokens.SNACK_DURATION_SHORT_MS,
            )

        if share_id and report_service:
            await report_service.delete_public_report(share_id)

        report["is_public"] = False
        report["share_id"] = ""
        report["share_url"] = ""
        if report_service:
            await report_service.update_report(
                report["id"],
                {
                    "is_public": False,
                    "share_id": "",
                    "share_url": "",
                },
            )
        if page:
            show_snack(
                page,
                "Removed from spaninsight.com public gallery.",
                success=True,
                duration=tokens.SNACK_DURATION_NORMAL_MS,
            )
    ui_state.rebuild()
