"""AppShell — top-level shell branching onboarding vs dashboard.

Uses @ft.component with hooks to conditionally render the active screen
based on tab selection and authentication state.
"""

import logging

import flet as ft
from flet import Control

from screens.home_screen import HomeScreen
from screens.onboarding_screen import OnboardingScreen
from screens.settings_screen import SettingsScreen
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


def _should_show_onboarding(state) -> bool:
    """True when the user hasn't completed onboarding or isn't authenticated."""
    return not state.onboarding_done


@ft.component
def AppShell() -> Control:
    """Top-level shell. Reads observable state; renders Onboarding or dashboard."""
    selected_tab, set_selected_tab = ft.use_state(0)
    controller = ft.use_context(ControllerMethodsCtx)
    state = ft.use_context(AppStateCtx)

    # Expose tab setter so controller can programmatically switch tabs
    controller.set_tab = set_selected_tab

    services = ft.use_context(ServiceCtx)

    # ── Sync NavigationBar & AppBar on page.views[0] ─────────────
    def _sync_bars():
        page = ft.context.page
        if not page or not page.views:
            return

        if _should_show_onboarding(state):
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
            set_selected_tab(idx)

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
            selected_index=selected_tab,
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

        theme_btn = ft.IconButton(
            icon=ft.Icons.LIGHT_MODE_ROUNDED
            if page.theme_mode == ft.ThemeMode.DARK
            else ft.Icons.DARK_MODE_ROUNDED,
            tooltip="Toggle Theme",
            on_click=lambda e: page.run_task(controller.toggle_theme),
        )

        colab_indicator = ft.Container(
            content=ft.Icon(
                ft.Icons.CLOUD_DONE_ROUNDED
                if state.colab_connected
                else ft.Icons.CLOUD_OFF_ROUNDED,
                size=20,
                color=ft.Colors.PRIMARY
                if state.colab_connected
                else ft.Colors.ON_SURFACE_VARIANT,
            ),
            tooltip="Colab: Connected"
            if state.colab_connected
            else "Colab: Disconnected",
            margin=ft.Margin(0, 0, 4, 0),
        )

        tag_text = (
            _TAB_NAMES[selected_tab]
            if 0 <= selected_tab < len(_TAB_NAMES)
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

        page.views[0].appbar = ft.AppBar(
            leading=page_tag,
            leading_width=120,
            actions=[colab_indicator, theme_btn, badge_container],
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
            selected_tab,
            state.onboarding_done,
            state.is_authenticated,
            state.colab_connected,
            state.credits_remaining,
            state.theme_mode,
        ],
    )

    # ── Screen switching ─────────────────────────────────────────
    if _should_show_onboarding(state):
        screen = OnboardingScreen()
    else:
        if selected_tab == 1:
            from screens.analysis_screen import AnalysisScreen

            screen = AnalysisScreen(key=ft.ValueKey("analysis"))
        elif selected_tab == 2:
            from screens.forms_screen import FormsScreen

            screen = FormsScreen(key=ft.ValueKey("forms"))
        elif selected_tab == 3:
            from screens.reports_screen import ReportsScreen

            screen = ReportsScreen(key=ft.ValueKey("reports"))
        elif selected_tab == 4:
            screen = SettingsScreen(key=ft.ValueKey("settings"))
        else:
            screen = HomeScreen(key=ft.ValueKey("home"))

    return ft.SafeArea(content=screen, expand=True)
