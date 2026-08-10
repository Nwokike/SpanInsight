"""Spaninsight v2 — Cloud-Powered Data Intelligence.

Main entry point: AppController bootstraps services and mounts the
React-like component tree via page.render().
"""

from __future__ import annotations

import asyncio
import logging
import sys

import flet as ft

from core.state import state
from core.theme import AppTheme
from services.ad_service import AdService
from services.credit_service import CreditService
from services.storage_service import StorageService

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("spaninsight")

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


class AppController:
    """Initializes services and mounts the component tree."""

    def __init__(self, page: ft.Page):
        self.page = page
        self.storage: StorageService | None = None
        self.credit_service: CreditService | None = None
        self.ad_service: AdService | None = None
        self.colab_service = None

    async def init(self):
        """Bootstrap services and mount the AppShell."""
        page = self.page

        page.title = "Spaninsight"
        page.favicon = "icon.png"
        page.fonts = {"Outfit": "assets/outfit.css"}

        page.theme = AppTheme.get_light_theme()
        page.dark_theme = AppTheme.get_dark_theme()
        page.theme.font_family = "Outfit"
        page.dark_theme.font_family = "Outfit"
        page.theme_mode = ft.ThemeMode.LIGHT
        state.theme_mode = page.theme_mode

        page.window.min_width = 360
        page.window.min_height = 600
        page.padding = 0
        page.spacing = 0

        page.on_error = self._on_error

        # ── Services ────────────────────────────────────────────
        self.storage = StorageService(page)
        self.credit_service = CreditService(page, self.storage)
        self.ad_service = AdService(page)
        await self.ad_service.gather_consent()

        from services.colab import ColabService

        self.colab_service = ColabService()
        page.run_task(self.colab_service.init)

        # Restore theme preference
        from core.constants import STORAGE_THEME

        try:
            saved_theme = await self.storage.get(STORAGE_THEME)
            if saved_theme == "dark":
                page.theme_mode = ft.ThemeMode.DARK
            elif saved_theme == "light":
                page.theme_mode = ft.ThemeMode.LIGHT
            else:
                page.theme_mode = ft.ThemeMode.SYSTEM
            state.theme_mode = page.theme_mode
        except Exception as e:
            logger.warning("Theme load failed: %s", e)

        state.credits_remaining = await self.credit_service.initialize()
        page.run_task(self.ad_service.preload_interstitial)

        page.on_disconnect = self._on_disconnect

        # ── Check onboarding status ─────────────────────────────
        from core.constants import STORAGE_ONBOARDING_DONE

        onboarding_done = await self.storage.get(STORAGE_ONBOARDING_DONE)
        if onboarding_done == "true":
            state.onboarding_done = True

        # ── Startup checks ──────────────────────────────────────
        page.run_task(self._startup_checks)

        # ── Connectivity monitor ────────────────────────────────
        from components.connectivity_monitor import (
            build_offline_banner,
            start_connectivity_monitor,
        )

        offline_banner = build_offline_banner()
        page.run_task(start_connectivity_monitor, page, offline_banner)

        # ── Build controller methods ────────────────────────────
        from state.controller_ctx import ControllerMethods, ControllerMethodsCtx
        from state.service_ctx import ServiceCtx, Services

        services = Services(
            colab=self.colab_service,
            credits=self.credit_service,
            storage=self.storage,
            page=page,
        )

        methods = ControllerMethods(
            start_analysis=self._start_analysis,
            toggle_theme=self._toggle_theme,
            check_update=self._startup_checks,
        )

        # ── Mount component tree ────────────────────────────────
        from app_shell import AppShell

        page.render(
            lambda: ServiceCtx(
                services,
                lambda: ControllerMethodsCtx(
                    methods,
                    lambda: AppShell(),
                ),
            )
        )
        logger.info("AppShell mounted — React-like UI active")

    def _start_analysis(self, autopilot: bool = False):
        """Switch to analysis tab, optionally in autopilot mode."""
        state.trigger_file_picker = True
        state.autopilot_enabled = autopilot

    async def _toggle_theme(self):
        """Toggle between light and dark theme."""
        page = self.page
        is_dark = page.theme_mode == ft.ThemeMode.DARK
        page.theme_mode = ft.ThemeMode.LIGHT if is_dark else ft.ThemeMode.DARK
        state.theme_mode = page.theme_mode

        if self.storage:
            from core.constants import STORAGE_THEME

            await self.storage.set(
                STORAGE_THEME,
                "light" if page.theme_mode == ft.ThemeMode.LIGHT else "dark",
            )
        page.update()

    def _on_error(self, e):
        """Global error handler."""
        logger.error("Page error: %s", e.data)
        try:
            self.page.snack_bar = ft.SnackBar(
                content=ft.Text(
                    "Something went wrong. Please try again.",
                    color=ft.Colors.WHITE,
                ),
                bgcolor=ft.Colors.BLACK,
            )
            self.page.snack_bar.open = True
            self.page.update()
        except Exception:
            pass

    async def _on_disconnect(self, e=None):
        """Flush storage and close HTTP client on app close."""
        try:
            await self.storage.flush()
        except Exception:
            pass
        try:
            from services.api_client import close_client

            await close_client()
        except Exception:
            pass

    async def _startup_checks(self):
        """Check API health and version requirements."""
        from services import ai as ai_service

        state.gateway_online = await ai_service.check_health()
        if not state.gateway_online:
            logger.warning("Gateway offline — AI features will use fallbacks")

        try:
            from core.constants import (
                API_BASE_URL,
                APP_CLIENT_ID,
                APP_VERSION,
                USER_AGENT,
            )
            from core.utils import parse_version
            from services.api_client import get_client

            client = get_client()
            resp = await client.get(
                f"{API_BASE_URL}/version",
                headers={"X-App-Secret": APP_CLIENT_ID, "User-Agent": USER_AGENT},
                timeout=5.0,
            )
            if resp.status_code == 200:
                data = resp.json()
                min_ver = data.get("min_version", "0.0.0")
                if parse_version(APP_VERSION) < parse_version(min_ver):
                    self.page.snack_bar = ft.SnackBar(
                        ft.Text(
                            "A required update is available. Please update Spaninsight."
                        ),
                        duration=8000,
                    )
                    self.page.snack_bar.open = True
                    self.page.update()
        except Exception:
            pass


async def main(page: ft.Page):
    """Main Flet application entry point."""
    controller = AppController(page)
    await controller.init()


if __name__ == "__main__":
    ft.run(main, assets_dir="assets")
