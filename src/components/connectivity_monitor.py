"""Global connectivity monitor - shows 'No Internet' banner.

Uses the real ft.Connectivity service (on_change for instant updates)
plus a fast polling fallback every 5 s. An OFFLINE declaration always
requires HTTP-probe confirmation, so transient dropouts (e.g. right
after the app resumes) never flash the banner. Returning to the
foreground triggers an immediate silent recheck.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable

import flet as ft

from core import theme, tokens
from core.state import state

logger = logging.getLogger(__name__)

_CHECK_INTERVAL = 5  # seconds between polls
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


def build_offline_banner() -> ft.Container:
    """'No Internet' banner - hidden by default; visibility is state-driven."""
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


async def _await_on_resume(coro):
    """Run an on_resume coroutine to completion as a page-lifetime task."""
    try:
        await coro
    except asyncio.CancelledError:
        raise
    except Exception as ex:
        logger.debug("on_resume task failed: %s", ex)


async def recheck_connectivity(page: ft.Page) -> bool:
    """Re-probe connectivity and update state immediately.

    AppShell owns the real banner and re-renders from ``state.is_online``,
    so flipping the observable field is enough to hide/show the banner.
    """
    online = await _check_online(page)
    if state.is_online == online and state.gateway_online == online:
        # Steady state: the poll runs every few seconds for the whole app
        # lifetime - a full page.update() on every tick starved the UI
        # (and destabilized desktop GL). Only touch anything on a flip.
        return online
    state.is_online = online
    state.gateway_online = online
    logger.info("Connectivity recheck: %s", "online" if online else "offline")
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


async def start_connectivity_monitor(
    page: ft.Page,
    banner: ft.Container | None = None,
    on_resume: Callable[[], None] | None = None,
):
    """Wire ft.Connectivity.on_change for instant updates + poll fallback.

    Call via `page.run_task(start_connectivity_monitor, page, banner)`.
    The task runs for the lifetime of the app; cancellation propagates
    cleanly because `asyncio.CancelledError` is a BaseException (it is
    not swallowed by the loop's `except Exception`).
    """
    # Wire real-time connectivity events if the service was registered.
    # Going ONLINE is applied instantly; going OFFLINE is only applied after
    # an HTTP probe confirms it - Android briefly reports NONE when the app
    # resumes, and trusting it blindly flashed the banner for seconds.
    connectivity: ft.Connectivity | None = getattr(page, "connectivity", None)

    if connectivity is not None:

        async def _confirm_offline():
            online = await _check_online(page)
            _apply_state(online, banner, page)

        def _on_change(e: ft.ConnectivityChangeEvent):
            if ft.ConnectivityType.NONE in e.connectivity:
                page.run_task(_confirm_offline)
                logger.info("Connectivity reported NONE - confirming via probe…")
            else:
                _apply_state(True, banner, page)
                logger.info("Connectivity changed: %s → online", e.connectivity)

        connectivity.on_change = _on_change

    # Returning to the foreground (mobile resume): recheck immediately so a
    # stale offline state clears without waiting for the next poll.
    def _on_lifecycle(e: ft.AppLifecycleStateChangeEvent):
        if e.state == ft.AppLifecycleState.SHOW:
            page.run_task(recheck_connectivity, page)
            if on_resume is not None:
                try:
                    result = on_resume()
                except Exception as ex:
                    logger.debug("on_resume callback failed: %s", ex)
                else:
                    # The hook is usually a coroutine function (e.g. the
                    # Colab resume ping) - it must be scheduled, not called,
                    # or it dies with "coroutine was never awaited".
                    if asyncio.iscoroutine(result):
                        page.run_task(_await_on_resume, result)

    try:
        page.on_app_lifecycle_state_change = _on_lifecycle
    except Exception as ex:
        logger.debug("Lifecycle events unavailable on this platform: %s", ex)

    # Polling loop - covers platforms where on_change may not fire
    while True:
        try:
            online = await _check_online(page)
            _apply_state(online, banner, page)
        except Exception:
            pass
        await asyncio.sleep(_CHECK_INTERVAL)
