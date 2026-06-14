"""Spaninsight — Privacy-First Data Intelligence.

Main entry point: page config, routing, service bootstrapping.
"""

from __future__ import annotations

import asyncio
import json
import pendulum
import logging
import sys
import shutil

import flet as ft

from core.theme import AppTheme
from core.state import state
from services.storage_service import StorageService
from services.credit_service import CreditService
from services.ad_service import AdService

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("spaninsight")

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


def _patch_matplotlib():
    """Monkeypatch matplotlib to prevent WebAgg crashes in Flet."""
    try:
        import matplotlib.backends.backend_webagg_core as webagg

        for cls_name in ["FigureManager", "FigureManagerWebAgg"]:
            if hasattr(webagg, cls_name):
                cls = getattr(webagg, cls_name)
                if hasattr(cls, "remove_web_socket"):
                    original_remove = cls.remove_web_socket

                    def make_safe_remove(orig):
                        def safe_remove(self, web_socket):
                            try:
                                self.web_sockets.discard(web_socket)
                            except Exception:
                                try:
                                    orig(self, web_socket)
                                except KeyError:
                                    pass

                        return safe_remove

                    cls.remove_web_socket = make_safe_remove(original_remove)
    except Exception as monkey_err:
        logger.warning(
            "Failed to monkeypatch matplotlib FigureManager: %s",
            monkey_err,
        )

    try:
        import matplotlib.backend_bases as _mb

        if not hasattr(_mb.FigureManagerBase, "add_web_socket"):
            _mb.FigureManagerBase.add_web_socket = lambda self, ws: None
        if not hasattr(_mb.FigureManagerBase, "remove_web_socket"):
            _mb.FigureManagerBase.remove_web_socket = lambda self, ws: None
        if not hasattr(_mb.FigureManagerBase, "handle_json"):
            _mb.FigureManagerBase.handle_json = lambda self, msg: None
    except Exception as agg_err:
        logger.warning("Failed to monkeypatch FigureManagerBase: %s", agg_err)


def cleanup_temp_files():
    """Wipe old temp files on startup to prevent storage bloat."""
    try:
        from core.utils import get_temp_dir

        temp_dir = get_temp_dir()
        if temp_dir.exists():
            shutil.rmtree(temp_dir, ignore_errors=True)
        temp_dir.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        logger.warning("Temp cleanup failed: %s", e)

    # Purge dataset cache files older than 7 days
    try:
        from services.dataset_cache import cleanup_stale

        cleanup_stale()
    except Exception as e:
        logger.warning("Dataset cache cleanup failed: %s", e)


async def main(page: ft.Page):
    """Main Flet application entry point."""
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

    def on_error(e):
        logger.error("Page error: %s", e.data)
        try:
            page.snack_bar = ft.SnackBar(
                content=ft.Text(
                    "Something went wrong. Please try again.", color=ft.Colors.WHITE
                ),
                bgcolor=ft.Colors.BLACK,
            )
            page.snack_bar.open = True
            page.update()
        except Exception:
            pass

    page.on_error = on_error

    _patch_matplotlib()
    import os

    assets_dir = os.path.join(os.path.dirname(__file__), "assets")
    for asset in ("icon.png", "logo.png"):
        if not os.path.exists(os.path.join(assets_dir, asset)):
            logger.warning("Missing asset: %s — app may display incorrectly", asset)

    storage = StorageService(page)
    from services.project_service import ProjectService

    project_service = ProjectService(page, storage)
    credit_service = CreditService(page, storage)
    ad_service = AdService(page)

    await project_service.initialize_projects()

    from core.constants import STORAGE_THEME

    try:
        saved_theme = await storage.get(STORAGE_THEME)
        if saved_theme == "dark":
            page.theme_mode = ft.ThemeMode.DARK
        elif saved_theme == "light":
            page.theme_mode = ft.ThemeMode.LIGHT
        else:
            page.theme_mode = ft.ThemeMode.SYSTEM
        state.theme_mode = page.theme_mode
    except Exception as e:
        logger.warning("Theme load failed (using default): %s", e)

    state.credits_remaining = await credit_service.initialize()
    page.run_task(ad_service.preload_interstitial)

    async def on_disconnect(e=None):
        """Flush storage and close HTTP client on app close."""
        try:
            await storage.flush()
        except Exception:
            pass
        try:
            from services.api_client import close_client

            await close_client()
        except Exception:
            pass

    page.on_disconnect = on_disconnect

    async def _startup_checks():
        from services import ai as ai_service

        state.gateway_online = await ai_service.check_health()
        if not state.gateway_online:
            logger.warning("Gateway offline — AI features will use fallbacks")

        try:
            from core.constants import (
                API_BASE_URL,
                APP_CLIENT_ID,
                USER_AGENT,
                APP_VERSION,
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
                    page.snack_bar = ft.SnackBar(
                        ft.Text(
                            "A required update is available. Please update Spaninsight."
                        ),
                        duration=8000,
                    )
                    page.snack_bar.open = True
                    page.update()
        except Exception:
            pass

    page.run_task(_startup_checks)
    nav_bar = ft.NavigationBar(
        selected_index=0,
        destinations=[
            ft.NavigationBarDestination(
                icon=ft.Icons.HOME_OUTLINED,
                selected_icon=ft.Icons.HOME_ROUNDED,
                label="Home",
            ),
            ft.NavigationBarDestination(
                icon=ft.Icons.DYNAMIC_FORM_OUTLINED,
                selected_icon=ft.Icons.DYNAMIC_FORM_ROUNDED,
                label="Forms",
            ),
            ft.NavigationBarDestination(
                icon=ft.Icons.ANALYTICS_OUTLINED,
                selected_icon=ft.Icons.ANALYTICS_ROUNDED,
                label="Analysis",
            ),
            ft.NavigationBarDestination(
                icon=ft.Icons.ASSESSMENT_OUTLINED,
                selected_icon=ft.Icons.ASSESSMENT_ROUNDED,
                label="Reports",
            ),
            ft.NavigationBarDestination(
                icon=ft.Icons.SETTINGS_OUTLINED,
                selected_icon=ft.Icons.SETTINGS_ROUNDED,
                label="Settings",
            ),
        ],
        bgcolor=ft.Colors.SURFACE,
        indicator_color=ft.Colors.with_opacity(0.12, ft.Colors.PRIMARY),
        label_behavior=ft.NavigationBarLabelBehavior.ALWAYS_SHOW,
    )

    TAB_ROUTES = ["/home", "/forms", "/analysis", "/reports", "/settings"]

    async def navigate(route: str):
        page.route = route
        await route_change()

    async def _save_recent_analysis():
        if not storage or not state.current_df_name:
            return
        try:
            recent_str = await storage.get("recent_analyses")
            recent = json.loads(recent_str) if recent_str else []

            recent = [
                s for s in recent if s.get("file_path") != state.current_file_path
            ]

            recent.insert(
                0,
                {
                    "file_path": state.current_file_path,
                    "df_name": state.current_df_name,
                    "df_rows": state.current_df_rows,
                    "df_cols": len(state.current_df_columns)
                    if state.current_df_columns
                    else 0,
                    "timestamp": pendulum.now().timestamp(),
                    "chart_count": len(getattr(state, "charts", [])),
                },
            )

            recent = recent[:10]
            await storage.set("recent_analyses", json.dumps(recent))
        except Exception as e:
            logger.warning("Failed to save recent analysis: %s", e)

    def on_import_file(e, autopilot: bool = False):
        nav_bar.selected_index = 1
        state.current_tab = 1
        state.trigger_file_picker = True
        state.autopilot_enabled = autopilot
        page.run_task(navigate, "/analysis")

    def on_nav_change(e):
        if getattr(state, "is_analyzing", False):
            nav_bar.selected_index = 2
            page.update()
            return

        index = e.control.selected_index
        old_tab = state.current_tab
        state.current_tab = index

        if old_tab == 1 and index != 1 and state.current_df is not None:
            page.run_task(_save_recent_analysis)

        page.run_task(navigate, TAB_ROUTES[index])

    nav_bar.on_change = on_nav_change

    def nav_to(route: str):
        page.run_task(navigate, route)

    _active_analysis_state = None

    async def route_change(e=None):
        nonlocal _active_analysis_state
        route = page.route
        logger.info("Route: %s", route)

        if _active_analysis_state and route != "/analysis":
            _active_analysis_state.dispose()
            _active_analysis_state = None

        page.views.clear()

        if route == "/home" or route == "/":
            from views.home_view import build_home_view

            view = build_home_view(
                page=page,
                on_import_file=on_import_file,
                on_navigate=nav_to,
                storage=storage,
            )
            page.views.append(view)
            nav_bar.selected_index = 0

        elif route == "/forms":
            from views.forms import build_forms_view

            view = build_forms_view(page=page)
            page.views.append(view)
            nav_bar.selected_index = 1

        elif route == "/analysis":
            from views.analysis import build_analysis_view
            from services.report_service import ReportService

            report_service = ReportService(storage)
            view = build_analysis_view(
                page=page,
                credit_service=credit_service,
                report_service=report_service,
            )
            _active_analysis_state = getattr(view, "_analysis_state", None)
            page.views.append(view)
            nav_bar.selected_index = 2

        elif route == "/reports" or route == "/report":
            from views.reports import build_report_view
            from services.report_service import ReportService

            report_service = ReportService(storage)
            view = build_report_view(
                page=page,
                report_service=report_service,
                ad_service=ad_service,
                storage=storage,
                credit_service=credit_service,
            )
            page.views.append(view)
            nav_bar.selected_index = 3

        elif route == "/settings":
            from views.settings_view import build_settings_view

            view = build_settings_view(
                page=page,
                credit_service=credit_service,
                storage=storage,
            )
            page.views.append(view)
            nav_bar.selected_index = 4

        elif route == "/onboarding":
            from views.onboarding_view import build_onboarding_view

            def _on_onboarding_done():
                page.run_task(navigate, "/home")

            view = build_onboarding_view(
                page=page,
                on_done=_on_onboarding_done,
                storage=storage,
            )
            page.views.append(view)

        else:
            from views.home_view import build_home_view

            view = build_home_view(
                page=page,
                on_import_file=on_import_file,
                on_navigate=nav_to,
                storage=storage,
            )
            page.views.append(view)

        if page.views:
            page.views[-1].navigation_bar = nav_bar

        if page.views and route != "/onboarding":
            top_view = page.views[-1]
            if top_view.appbar:
                from components.project_switcher import build_project_switcher
                from components.credit_badge import build_credit_badge

                switcher = build_project_switcher(page, project_service)

                async def _global_toggle_theme(e=None):
                    is_dark = page.theme_mode == ft.ThemeMode.DARK or (
                        page.theme_mode == ft.ThemeMode.SYSTEM
                        and page.platform_brightness == ft.Brightness.DARK
                    )
                    page.theme_mode = (
                        ft.ThemeMode.LIGHT if is_dark else ft.ThemeMode.DARK
                    )
                    state.theme_mode = page.theme_mode

                    if storage:
                        from core.constants import STORAGE_THEME

                        await storage.set(
                            STORAGE_THEME,
                            "light"
                            if page.theme_mode == ft.ThemeMode.LIGHT
                            else "dark",
                        )

                    theme_btn.icon = (
                        ft.Icons.LIGHT_MODE_ROUNDED
                        if page.theme_mode == ft.ThemeMode.DARK
                        else ft.Icons.DARK_MODE_ROUNDED
                    )
                    page.update()

                theme_btn = ft.IconButton(
                    icon=ft.Icons.LIGHT_MODE_ROUNDED
                    if page.theme_mode == ft.ThemeMode.DARK
                    else ft.Icons.DARK_MODE_ROUNDED,
                    tooltip="Toggle Theme",
                    disabled=False,
                    on_click=lambda e: page.run_task(_global_toggle_theme),
                )

                from components.credit_badge import show_credits_dialog

                badge = build_credit_badge(state.credits_remaining)
                badge_container = ft.Container(
                    content=badge,
                    margin=ft.Margin(0, 0, 16, 0),
                    on_click=lambda e: show_credits_dialog(page, credit_service),
                )

                page_tags = {
                    "/home": "Home",
                    "/forms": "Forms",
                    "/analysis": "Analysis",
                    "/reports": "Reports",
                    "/settings": "Settings",
                }
                tag_text = page_tags.get(route, "Workspace")
                page_tag = ft.Container(
                    content=ft.Text(
                        tag_text,
                        size=14,
                        weight=ft.FontWeight.BOLD,
                        color=ft.Colors.ON_SURFACE,
                    ),
                    padding=ft.Padding(16, 0, 0, 0),
                    alignment=ft.Alignment.CENTER_LEFT,
                )
                top_view.appbar.leading = page_tag
                top_view.appbar.leading_width = 100
                top_view.appbar.title = switcher
                top_view.appbar.actions = [theme_btn, badge_container]
                top_view.appbar.center_title = True
                top_view.appbar.bgcolor = ft.Colors.TRANSPARENT

        page.update()

    async def view_pop(e):
        page.views.pop()
        if page.views:
            top = page.views[-1]
            page.route = top.route
            try:
                nav_bar.selected_index = TAB_ROUTES.index(page.route)
            except ValueError:
                pass
        page.update()

    page.on_route_change = route_change
    page.on_view_pop = view_pop

    async def _initial_route():
        from core.constants import STORAGE_ONBOARDING_DONE

        onboarding_done = await storage.get(STORAGE_ONBOARDING_DONE)
        if onboarding_done == "true":
            await navigate("/home")
        else:
            await navigate("/onboarding")

    page.run_task(_initial_route)


if __name__ == "__main__":
    cleanup_temp_files()
    ft.run(main, assets_dir="assets")
