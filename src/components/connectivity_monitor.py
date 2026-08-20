"""Global connectivity monitor - shows 'No Internet' banner.

Uses the real ft.Connectivity service (on_change for instant updates)
plus a polling fallback every 15 s. Never forces re-onboarding when
offline - just shows a non-intrusive banner with a manual retry button.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable

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


async def _check_online(page: ft.Page) -> bool:
    """Combine the OS-level connectivity service with an HTTP probe."""
    online = False
    connectivity = getattr(page, "connectivity", None)
    if connectivity is not None:
        try:
            online = (
                ft.ConnectivityType.NONE not in await connectivity.get_connectivity()
            )
        except Exception:
            online = False
    if online:
        return True
    return await _http_online()


def build_offline_banner(on_retry: Callable[[], None] | None = None) -> ft.Container:
    """'No Internet' banner - hidden by default, optional Retry action."""
    controls: list[ft.Control] = [
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
            no_wrap=True,
            overflow=ft.TextOverflow.ELLIPSIS,
        ),
    ]
    if on_retry is not None:
        controls.append(
            ft.TextButton(
                "Retry",
                icon=ft.Icons.REFRESH_ROUNDED,
                on_click=lambda _: on_retry(),
                style=ft.ButtonStyle(
                    color=ft.Colors.WHITE,
                    padding=tokens.SPACE_XS,
                ),
            )
        )
    return ft.Container(
        content=ft.Row(
            controls=controls,
            spacing=tokens.SPACE_SM,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        padding=ft.Padding(
            tokens.SPACE_LG, tokens.SPACE_SM, tokens.SPACE_LG, tokens.SPACE_SM
        ),
        bgcolor=theme.ERROR,
        visible=False,
    )


async def recheck_connectivity(page: ft.Page) -> bool:
    """Manual retry: re-probe connectivity and update state immediately.

    AppShell owns the real banner and re-renders from ``state.is_online``,
    so flipping the observable field is enough to hide/show the banner.
    """
    online = await _check_online(page)
    state.is_online = online
    state.gateway_online = online
    logger.info("Manual connectivity recheck: %s", "online" if online else "offline")
    try:
        if page:
            page.update()
    except Exception:
        pass
    return online


def _apply_state(online: bool, banner: ft.Container | None, page: ft.Page):
    """Update state and banner visibility atomically."""
    state.is_online = online
    state.gateway_online = online
    if banner is not None:
        if banner.visible == online:  # banner shows when OFFLINE (not online)
            banner.visible = not online
        try:
            page.update()
        except Exception:
            pass


async def start_connectivity_monitor(page: ft.Page, banner: ft.Container | None = None):
    """Wire ft.Connectivity.on_change for instant updates + poll fallback.

    Call via `page.run_task(start_connectivity_monitor, page, banner)`.
    The task runs for the lifetime of the app; cancellation propagates
    cleanly because `asyncio.CancelledError` is a BaseException (it is
    not swallowed by the loop's `except Exception`).
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

    # Polling loop - covers platforms where on_change may not fire
    while True:
        try:
            online = await _check_online(page)
            _apply_state(online, banner, page)
        except Exception:
            pass
        await asyncio.sleep(_CHECK_INTERVAL)
