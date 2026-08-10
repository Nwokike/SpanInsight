"""Global connectivity monitor — shows 'No Internet' banner.

Ported from CollabShell's approach: instead of defaulting back to
onboarding when offline, we show a non-intrusive banner at the
top of the screen and let the user continue using cached data.
"""

from __future__ import annotations

import asyncio
import logging

import flet as ft

from core import theme, tokens
from core.state import state

logger = logging.getLogger(__name__)

_CHECK_INTERVAL = 15  # seconds between checks
_CHECK_URL = "https://clients3.google.com/generate_204"
_CHECK_TIMEOUT = 5


async def _is_online() -> bool:
    """Quick connectivity check — hit Google's 204 endpoint."""
    try:
        import urllib.request

        req = urllib.request.Request(_CHECK_URL, method="HEAD")
        resp = await asyncio.to_thread(
            urllib.request.urlopen, req, timeout=_CHECK_TIMEOUT
        )
        return resp.status == 204
    except Exception:
        return False


def build_offline_banner() -> ft.Container:
    """Build a dismissible 'No Internet' banner (hidden by default)."""
    return ft.Container(
        content=ft.Row(
            controls=[
                ft.Icon(ft.Icons.WIFI_OFF_ROUNDED, size=16, color=ft.Colors.WHITE),
                ft.Text(
                    "No internet connection",
                    size=tokens.FONT_SM,
                    color=ft.Colors.WHITE,
                    weight=ft.FontWeight.W_600,
                    expand=True,
                ),
                ft.Text(
                    "Some features are unavailable",
                    size=tokens.FONT_XS,
                    color=ft.Colors.with_opacity(0.8, ft.Colors.WHITE),
                ),
            ],
            spacing=tokens.SPACE_SM,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        padding=ft.Padding(
            tokens.SPACE_LG, tokens.SPACE_SM, tokens.SPACE_LG, tokens.SPACE_SM
        ),
        bgcolor=theme.ERROR,
        visible=False,
    )


async def start_connectivity_monitor(page: ft.Page, banner: ft.Container):
    """Background task that checks connectivity and shows/hides the banner.

    Call via `page.run_task(start_connectivity_monitor, page, banner)`.
    """
    while True:
        try:
            online = await _is_online()
            state.gateway_online = online
            if banner.visible == online:
                banner.visible = not online
                page.update()
        except Exception:
            pass
        await asyncio.sleep(_CHECK_INTERVAL)
