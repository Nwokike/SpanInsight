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
        from services.project_service import ProjectService

        self.project_service = ProjectService(self.storage)
        self.ad_service = AdService(page)
        await self.ad_service.gather_consent()

        from services.colab import ColabService

        self.colab_service = ColabService()
        page.run_task(self.colab_service.init)

        # Register global FilePicker service
        file_picker = ft.FilePicker()
        page.services.append(file_picker)
        page.file_picker = file_picker

        # Register Connectivity service
        connectivity = ft.Connectivity()
        page.services.append(connectivity)
        page.connectivity = connectivity

        # Restore theme preference
        from core.constants import STORAGE_THEME

        try:
            saved_theme = await self.storage.get(STORAGE_THEME)
            theme_map = {
                "dark": ft.ThemeMode.DARK,
                "system": ft.ThemeMode.SYSTEM,
                "light": ft.ThemeMode.LIGHT,
            }
            page.theme_mode = theme_map.get(saved_theme, ft.ThemeMode.SYSTEM)
            state.theme_mode = page.theme_mode
        except Exception as e:
            logger.warning("Theme load failed: %s", e)

        state.credits_remaining = await self.credit_service.initialize()
        page.run_task(self.ad_service.preload_interstitial)

        page.on_disconnect = self._on_disconnect

        # ── Startup: auth check + route decision ─────────────────
        page.run_task(self._initial_route)

        # ── Connectivity monitor (updates state.is_online) ─────────
        from components.connectivity_monitor import (
            build_offline_banner,
            start_connectivity_monitor,
        )

        _stub_banner = (
            build_offline_banner()
        )  # monitor updates state.is_online; AppShell owns the real banner
        page.run_task(start_connectivity_monitor, page, _stub_banner)

        # ── Build controller methods ────────────────────────────
        from state.controller_ctx import ControllerMethods, ControllerMethodsCtx
        from state.service_ctx import ServiceCtx, Services

        services = Services(
            colab=self.colab_service,
            credits=self.credit_service,
            storage=self.storage,
            projects=self.project_service,
            page=page,
        )

        methods = ControllerMethods(
            start_analysis=self._start_analysis,
            navigate_tab=self.navigate_tab,
            toggle_theme=self._toggle_theme,
            check_update=self._startup_checks,
            show_snack=self.show_snack,
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
        logger.info("SpanInsight application shell mounted")

    def navigate_tab(self, idx: int):
        """Navigate to a specific tab index."""
        state.current_tab = idx

    def show_snack(self, message: str):
        """Show a snackbar message."""
        try:
            self.page.snack_bar = ft.SnackBar(content=ft.Text(message))
            self.page.snack_bar.open = True
            self.page.update()
        except Exception:
            pass

    def _start_analysis(self, autopilot: bool = False):
        """Switch to analysis tab, optionally in autopilot mode."""
        state.autopilot_enabled = autopilot
        state.current_tab = 1
        state.trigger_file_picker = True

    async def _toggle_theme(self):
        """Toggle between dark, light, and system theme matching DDGS pattern."""
        page = self.page
        if page.theme_mode == ft.ThemeMode.DARK:
            page.theme_mode = ft.ThemeMode.LIGHT
            theme_str = "light"
        elif page.theme_mode == ft.ThemeMode.LIGHT:
            page.theme_mode = ft.ThemeMode.SYSTEM
            theme_str = "system"
        else:
            page.theme_mode = ft.ThemeMode.DARK
            theme_str = "dark"

        state.theme_mode = page.theme_mode

        if self.storage:
            from core.constants import STORAGE_THEME

            await self.storage.set(STORAGE_THEME, theme_str)
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

    async def _initial_route(self):
        """Determine startup route using Colab Shell's proven pattern."""
        from core.constants import (
            STORAGE_DEFAULT_GPU,
            STORAGE_DEFAULT_TIMEOUT,
            STORAGE_DEFAULT_TPU,
            STORAGE_KEEP_ALIVE,
            STORAGE_ONBOARDING_DONE,
        )

        # Restore hardware defaults from storage
        try:
            saved_gpu = await self.storage.get(STORAGE_DEFAULT_GPU)
            if saved_gpu:
                state.default_gpu = saved_gpu
            saved_tpu = await self.storage.get(STORAGE_DEFAULT_TPU)
            if saved_tpu:
                state.default_tpu = saved_tpu
            saved_timeout = await self.storage.get(STORAGE_DEFAULT_TIMEOUT)
            if saved_timeout:
                try:
                    state.default_timeout = int(saved_timeout)
                except ValueError:
                    pass
            saved_ka = await self.storage.get(STORAGE_KEEP_ALIVE)
            if saved_ka is not None:
                state.keep_alive_enabled = saved_ka == "true"
        except Exception as e:
            logger.warning("Settings restore failed: %s", e)

        # Check connectivity — never force re-onboarding when offline
        try:
            conn_types = await self.page.connectivity.get_connectivity()
            state.is_online = ft.ConnectivityType.NONE not in conn_types
        except Exception:
            state.is_online = True  # Assume online if check fails

        if not state.is_online:
            # Offline on launch: honour saved onboarding/auth, skip auth check
            onboarding_done = await self.storage.get(STORAGE_ONBOARDING_DONE)
            state.onboarding_done = onboarding_done == "true"
            # If they've onboarded before, let them in — just no Colab features
            if state.onboarding_done:
                state.is_authenticated = True  # trust stored auth offline
            state.app_ready = True
            return  # AppShell will show offline banner via connectivity monitor

        # Online — check if token is still valid
        try:
            auth_info = await self.colab_service.check_auth()
            state.is_authenticated = auth_info.get("authenticated", False)
            state.auth_email = auth_info.get("email", "")
        except Exception as e:
            logger.warning("Auth check failed at boot: %s", e)
            state.is_authenticated = False

        if state.is_authenticated:
            # Valid token → mark onboarding done and go straight to app
            state.onboarding_done = True
            await self.storage.set(STORAGE_ONBOARDING_DONE, "true")

            # Discover and attach to existing active Colab session
            try:
                sessions = await self.colab_service.list_sessions()
                if sessions and isinstance(sessions, list):
                    active = sessions[0]
                    state.active_session_name = active["name"]
                    state.session_hardware = (
                        "CPU"
                        if active.get("accelerator") == "NONE"
                        else active.get("accelerator", "CPU")
                    )
                    state.colab_connected = True
                    logger.info(
                        "Auto-attached to active Colab session: %s (%s)",
                        state.active_session_name,
                        state.session_hardware,
                    )
            except Exception as ex:
                logger.debug("Session auto-discovery: %s", ex)
        else:
            # No valid token → check if they've ever onboarded
            onboarding_done = await self.storage.get(STORAGE_ONBOARDING_DONE)
            state.onboarding_done = onboarding_done == "true"

        # Run health/version checks in background
        self.page.run_task(self._startup_checks)

        # Signal AppShell that boot is complete
        state.app_ready = True

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
