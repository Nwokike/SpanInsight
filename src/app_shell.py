"""AppShell — top-level shell branching onboarding vs dashboard.

Uses @ft.component with hooks to conditionally render the active screen
based on tab selection and authentication state.
"""

from __future__ import annotations

import logging

import flet as ft
from flet import Control

from core import tokens
from state import AppStateCtx
from state.controller_ctx import ControllerMethodsCtx
from state.service_ctx import ServiceCtx

logger = logging.getLogger("AppShell")

_TAB_NAMES = ("Home", "Analysis", "Forms", "Reports", "Settings")
_TAB_ICONS = (
    ft.Icons.HOME_OUTLINED,
    ft.Icons.INSIGHTS_OUTLINED,
    ft.Icons.DYNAMIC_FORM_OUTLINED,
    ft.Icons.ASSESSMENT_OUTLINED,
    ft.Icons.SETTINGS_OUTLINED,
)
_TAB_SELECTED_ICONS = (
    ft.Icons.HOME_ROUNDED,
    ft.Icons.INSIGHTS_ROUNDED,
    ft.Icons.DYNAMIC_FORM_ROUNDED,
    ft.Icons.ASSESSMENT_ROUNDED,
    ft.Icons.SETTINGS_ROUNDED,
)


@ft.component
def AppShell() -> Control:
    """Top-level shell. Reads observable state; renders Onboarding or dashboard."""
    controller = ft.use_context(ControllerMethodsCtx)
    state = ft.use_context(AppStateCtx)
    services = ft.use_context(ServiceCtx)
    is_connecting, set_is_connecting = ft.use_state(False)

    # ── Sync NavigationBar & AppBar on page.views[0] ─────────────
    # MUST be declared and registered at top level before any conditional return!
    async def _sync_bars():
        page = ft.context.page
        if not page or not page.views:
            return

        if (
            not state.app_ready
            or not state.onboarding_done
            or state.active_subview == "projects"
        ):
            if page.views[0].navigation_bar is not None:
                page.views[0].navigation_bar = None
            if page.views[0].appbar is not None:
                page.views[0].appbar = None
            try:
                page.update()
            except Exception:
                pass
            return

        def _on_tab_change(e):
            idx = e.control.selected_index
            logger.info("Navigated to tab '%s' (index %d)", _TAB_NAMES[idx], idx)
            controller.navigate_tab(idx)

        destinations = [
            ft.NavigationBarDestination(
                icon=icon,
                selected_icon=sel_icon,
                label=label,
            )
            for icon, sel_icon, label in zip(
                _TAB_ICONS, _TAB_SELECTED_ICONS, _TAB_NAMES, strict=True
            )
        ]
        page.views[0].navigation_bar = ft.NavigationBar(
            destinations=destinations,
            selected_index=state.current_tab,
            on_change=_on_tab_change,
            bgcolor=ft.Colors.SURFACE,
            indicator_color=ft.Colors.with_opacity(0.12, ft.Colors.PRIMARY),
            label_behavior=ft.NavigationBarLabelBehavior.ALWAYS_SHOW,
        )

        from components.credit_badge import build_credit_badge, show_credits_dialog

        badge = build_credit_badge(state.credits_remaining)
        badge_container = ft.Container(
            content=badge,
            margin=ft.Margin(0, 0, 16, 0),
            on_click=lambda e: show_credits_dialog(page, services.credits),
        )

        def _get_theme_icon():
            if page.theme_mode == ft.ThemeMode.DARK:
                return ft.Icons.DARK_MODE_ROUNDED
            elif page.theme_mode == ft.ThemeMode.LIGHT:
                return ft.Icons.LIGHT_MODE_ROUNDED
            return ft.Icons.BRIGHTNESS_AUTO_ROUNDED

        def _get_theme_tooltip():
            if page.theme_mode == ft.ThemeMode.DARK:
                return "Theme: Dark (Click for Light)"
            elif page.theme_mode == ft.ThemeMode.LIGHT:
                return "Theme: Light (Click for System)"
            return "Theme: System (Click for Dark)"

        theme_btn = ft.IconButton(
            icon=_get_theme_icon(),
            tooltip=_get_theme_tooltip(),
            on_click=lambda e: page.run_task(controller.toggle_theme),
        )

        async def _connect_colab_header():
            if is_connecting:
                return
            set_is_connecting(True)
            try:
                res = await services.colab.ensure_active_session()
                if res:
                    state.active_session_name = res.get("name", "")
                    state.session_hardware = (
                        "CPU"
                        if res.get("accelerator") == "NONE"
                        else res.get("accelerator", "CPU")
                    )
                    state.colab_connected = True
                    if page:
                        from core.utils import show_snack

                        show_snack(
                            page,
                            f"Connected to Colab ({state.session_hardware})",
                            success=True,
                        )
            except Exception as ex:
                if page:
                    from core.utils import show_snack

                    show_snack(page, f"Colab connect failed: {ex}", error=True)
            finally:
                set_is_connecting(False)

        if is_connecting:
            colab_indicator = ft.Container(
                content=ft.Row(
                    [
                        ft.ProgressRing(width=12, height=12, stroke_width=2),
                        ft.Text(
                            "Connecting…",
                            size=tokens.FONT_XS,
                            color=ft.Colors.PRIMARY,
                        ),
                    ],
                    spacing=tokens.SPACE_XXS,
                    alignment=ft.MainAxisAlignment.CENTER,
                ),
                padding=ft.Padding(
                    tokens.SPACE_SM, tokens.SPACE_XXS, tokens.SPACE_SM, tokens.SPACE_XXS
                ),
                border_radius=tokens.RADIUS_SM,
                bgcolor=ft.Colors.with_opacity(0.12, ft.Colors.PRIMARY),
                margin=ft.Margin(0, 0, 4, 0),
            )
        elif state.colab_connected and state.active_session_name:
            colab_indicator = ft.Container(
                content=ft.Row(
                    [
                        ft.Icon(
                            ft.Icons.CLOUD_DONE_ROUNDED,
                            size=16,
                            color=ft.Colors.PRIMARY,
                        ),
                        ft.Text(
                            state.session_hardware,
                            size=tokens.FONT_XS,
                            weight=ft.FontWeight.W_600,
                            color=ft.Colors.PRIMARY,
                        ),
                    ],
                    spacing=tokens.SPACE_XXS,
                    alignment=ft.MainAxisAlignment.CENTER,
                ),
                padding=ft.Padding(
                    tokens.SPACE_SM, tokens.SPACE_XXS, tokens.SPACE_SM, tokens.SPACE_XXS
                ),
                border_radius=tokens.RADIUS_SM,
                bgcolor=ft.Colors.with_opacity(0.12, ft.Colors.PRIMARY),
                tooltip=f"Colab Connected: {state.active_session_name} ({state.session_hardware})",
                margin=ft.Margin(0, 0, 4, 0),
            )
        else:
            colab_indicator = ft.Container(
                content=ft.Row(
                    [
                        ft.Icon(
                            ft.Icons.CLOUD_OFF_ROUNDED,
                            size=16,
                            color=ft.Colors.ON_SURFACE_VARIANT,
                        ),
                        ft.Text(
                            "Connect",
                            size=tokens.FONT_XS,
                            color=ft.Colors.ON_SURFACE_VARIANT,
                        ),
                    ],
                    spacing=tokens.SPACE_XXS,
                    alignment=ft.MainAxisAlignment.CENTER,
                ),
                padding=ft.Padding(
                    tokens.SPACE_SM, tokens.SPACE_XXS, tokens.SPACE_SM, tokens.SPACE_XXS
                ),
                border_radius=tokens.RADIUS_SM,
                border=ft.Border.all(
                    1, ft.Colors.with_opacity(0.2, ft.Colors.ON_SURFACE)
                ),
                tooltip="Colab Disconnected — Click to connect",
                margin=ft.Margin(0, 0, 4, 0),
                on_click=lambda _: page.run_task(_connect_colab_header),
            )

        tag_text = (
            _TAB_NAMES[state.current_tab]
            if 0 <= state.current_tab < len(_TAB_NAMES)
            else "Spaninsight"
        )
        page_tag = ft.Container(
            content=ft.Text(
                tag_text,
                size=16,
                weight=ft.FontWeight.BOLD,
                color=ft.Colors.ON_SURFACE,
            ),
            padding=ft.Padding(16, 0, 0, 0),
            alignment=ft.Alignment.CENTER_LEFT,
        )

        # Global busy chip — generation/autopilot can take 1-2+ minutes at the
        # gateway; users navigating other tabs must still SEE that it's running.
        ai_busy = state.is_analyzing or state.autopilot_running
        ai_busy_chip = ft.Container(
            content=ft.Row(
                [
                    ft.ProgressRing(width=12, height=12, stroke_width=2),
                    ft.Text(
                        "AI working…",
                        size=tokens.FONT_XS,
                        weight=ft.FontWeight.W_600,
                        color=ft.Colors.PRIMARY,
                    ),
                ],
                spacing=tokens.SPACE_XXS,
                tight=True,
            ),
            padding=ft.Padding(
                tokens.SPACE_SM, tokens.SPACE_XXS, tokens.SPACE_SM, tokens.SPACE_XXS
            ),
            border_radius=tokens.RADIUS_SM,
            bgcolor=ft.Colors.with_opacity(0.12, ft.Colors.PRIMARY),
            tooltip="An AI task is running — results appear on the Analysis tab",
            margin=ft.Margin(0, 0, 4, 0),
            visible=ai_busy,
        )

        page.views[0].appbar = ft.AppBar(
            leading=page_tag,
            leading_width=120,
            actions=[ai_busy_chip, colab_indicator, theme_btn, badge_container],
            center_title=True,
            bgcolor=ft.Colors.TRANSPARENT,
        )

        try:
            page.update()
        except Exception:
            pass

    ft.use_effect(
        _sync_bars,
        [
            state.app_ready,
            state.current_tab,
            state.active_subview,
            state.onboarding_done,
            state.is_authenticated,
            state.colab_connected,
            state.active_session_name,
            state.session_hardware,
            state.credits_remaining,
            state.theme_mode,
            state.is_analyzing,
            state.autopilot_running,
            is_connecting,
        ],
    )

    # ── Screen switching ─────────────────────────────────────────
    if not state.app_ready:
        screen = ft.Container(
            content=ft.Column(
                [
                    ft.Image(
                        src="icon.png", width=72, height=72, fit=ft.BoxFit.CONTAIN
                    ),
                    ft.Container(height=24),
                    ft.ProgressRing(width=28, height=28, stroke_width=3),
                ],
                alignment=ft.MainAxisAlignment.CENTER,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            expand=True,
            alignment=ft.Alignment.CENTER,
        )
    elif not state.onboarding_done:
        from screens.onboarding_screen import OnboardingScreen

        screen = OnboardingScreen()
    elif state.active_subview == "projects":
        from screens.projects import ProjectsScreen

        screen = ProjectsScreen(key=ft.ValueKey("projects"))
    else:
        if state.current_tab == 1:
            from screens.analysis import AnalysisScreen

            screen = AnalysisScreen(key=ft.ValueKey("analysis"))
        elif state.current_tab == 2:
            from screens.forms import FormsScreen

            screen = FormsScreen(key=ft.ValueKey("forms"))
        elif state.current_tab == 3:
            from screens.reports import ReportsScreen

            screen = ReportsScreen(key=ft.ValueKey("reports"))
        elif state.current_tab == 4:
            from screens.settings import SettingsScreen

            screen = SettingsScreen(key=ft.ValueKey("settings"))
        else:
            from screens.home import HomeScreen

            screen = HomeScreen(key=ft.ValueKey("home"))

    # ── Offline banner (shown by connectivity monitor) ───────────
    from components.connectivity_monitor import build_offline_banner

    offline_banner = build_offline_banner()
    if not state.is_online:
        offline_banner.visible = True

    return ft.Column(
        controls=[
            offline_banner,
            ft.SafeArea(content=screen, expand=True),
        ],
        expand=True,
        spacing=0,
    )
