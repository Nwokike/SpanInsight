"""Global connectivity monitor — shows 'No Internet' banner.

Uses the real ft.Connectivity service (on_change for instant updates)
plus a polling fallback every 15 s. Never forces re-onboarding when
offline — just shows a non-intrusive banner.
"""

from __future__ import annotations

import asyncio
import logging

import flet as ft

from core import theme, tokens
from core.state import state

logger = logging.getLogger(__name__)

_CHECK_INTERVAL = 15  # seconds between polls
_CHECK_URL = "https://clients3.google.com/generate_204"
_CHECK_TIMEOUT = 5


async def _http_online() -> bool:
    """Quick HTTP connectivity check via Google's 204 endpoint."""
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
    """Dismissible 'No Internet' banner — hidden by default."""
    return ft.Container(
        content=ft.Row(
            controls=[
                ft.Icon(
                    ft.Icons.WIFI_OFF_ROUNDED,
                    size=tokens.ICON_SM,
                    color=ft.Colors.WHITE,
                ),
                ft.Text(
                    "No internet connection",
                    size=tokens.FONT_SM,
                    color=ft.Colors.WHITE,
                    weight=ft.FontWeight.W_600,
                    expand=True,
                ),
                ft.Text(
                    "Colab features unavailable",
                    size=tokens.FONT_XS,
                    color=ft.Colors.with_opacity(tokens.OPACITY_HEAVY, ft.Colors.WHITE),
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


def _apply_state(online: bool, banner: ft.Container, page: ft.Page):
    """Update state and banner visibility atomically."""
    state.is_online = online
    state.gateway_online = online
    if banner.visible == online:  # banner shows when OFFLINE (not online)
        banner.visible = not online
        try:
            page.update()
        except Exception:
            pass


async def start_connectivity_monitor(page: ft.Page, banner: ft.Container):
    """Wire ft.Connectivity.on_change for instant updates + poll fallback.

    Call via `page.run_task(start_connectivity_monitor, page, banner)`.
    """
    # Wire real-time connectivity events if the service was registered
    connectivity: ft.Connectivity | None = getattr(page, "connectivity", None)

    if connectivity is not None:

        def _on_change(e: ft.ConnectivityChangeEvent):
            online = ft.ConnectivityType.NONE not in e.connectivity
            _apply_state(online, banner, page)
            logger.info(
                "Connectivity changed: %s → %s",
                e.connectivity,
                "online" if online else "offline",
            )

        connectivity.on_change = _on_change

    # Polling loop — covers platforms where on_change may not fire
    while True:
        try:
            online = await _http_online()
            _apply_state(online, banner, page)
        except Exception:
            pass
        await asyncio.sleep(_CHECK_INTERVAL)
