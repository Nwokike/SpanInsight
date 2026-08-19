"""AppShell - top-level shell branching onboarding vs dashboard.

Uses @ft.component to declaratively render the active screen, top app bar,
and bottom navigation bar based on tab selection and authentication state.
"""

from __future__ import annotations

import logging

import flet as ft
from flet import Control

from components.credit_badge import build_credit_badge, show_credits_dialog
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
    page = ft.context.page
    is_connecting, set_is_connecting = ft.use_state(False)

    show_dashboard = bool(
        state.app_ready
        and state.onboarding_done
        and state.is_authenticated
        and state.active_subview != "projects"
    )

    # ── Colab Connect Action ─────────────────────────────────────
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

    # ── Top Bar Assembly ─────────────────────────────────────────
    top_bar = None
    if show_dashboard:
        tag_text = (
            _TAB_NAMES[state.current_tab]
            if 0 <= state.current_tab < len(_TAB_NAMES)
            else "Spaninsight"
        )
        page_tag = ft.Text(
            tag_text,
            size=tokens.FONT_HEADING,
            weight=ft.FontWeight.BOLD,
            color=ft.Colors.ON_SURFACE,
        )

        badge = build_credit_badge(state.credits_remaining)
        badge_container = ft.Container(
            content=badge,
            margin=ft.Margin(
                tokens.SPACE_NONE,
                tokens.SPACE_NONE,
                tokens.SPACE_MD,
                tokens.SPACE_NONE,
            ),
            on_click=lambda e: (
                show_credits_dialog(page, services.credits) if page else None
            ),
        )

        def _get_theme_icon():
            if page and page.theme_mode == ft.ThemeMode.DARK:
                return ft.Icons.DARK_MODE_ROUNDED
            elif page and page.theme_mode == ft.ThemeMode.LIGHT:
                return ft.Icons.LIGHT_MODE_ROUNDED
            return ft.Icons.BRIGHTNESS_AUTO_ROUNDED

        def _get_theme_tooltip():
            if page and page.theme_mode == ft.ThemeMode.DARK:
                return "Theme: Dark (Click for Light)"
            elif page and page.theme_mode == ft.ThemeMode.LIGHT:
                return "Theme: Light (Click for System)"
            return "Theme: System (Click for Dark)"

        theme_btn = ft.IconButton(
            icon=_get_theme_icon(),
            tooltip=_get_theme_tooltip(),
            on_click=lambda e: page.run_task(controller.toggle_theme) if page else None,
        )

        if is_connecting:
            colab_indicator = ft.Container(
                content=ft.Row(
                    [
                        ft.ProgressRing(
                            width=tokens.PROGRESS_RING_XS,
                            height=tokens.PROGRESS_RING_XS,
                            stroke_width=tokens.PROGRESS_RING_STROKE_THIN,
                        ),
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
                    tokens.SPACE_SM,
                    tokens.SPACE_XXS,
                    tokens.SPACE_SM,
                    tokens.SPACE_XXS,
                ),
                border_radius=tokens.RADIUS_SM,
                bgcolor=ft.Colors.with_opacity(
                    tokens.OPACITY_CONTAINER, ft.Colors.PRIMARY
                ),
                margin=ft.Margin(
                    tokens.SPACE_NONE,
                    tokens.SPACE_NONE,
                    tokens.SPACE_XS,
                    tokens.SPACE_NONE,
                ),
            )
        elif state.colab_connected and state.active_session_name:
            colab_indicator = ft.Container(
                content=ft.Row(
                    [
                        ft.Icon(
                            ft.Icons.CLOUD_DONE_ROUNDED,
                            size=tokens.ICON_SM,
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
                    tokens.SPACE_SM,
                    tokens.SPACE_XXS,
                    tokens.SPACE_SM,
                    tokens.SPACE_XXS,
                ),
                border_radius=tokens.RADIUS_SM,
                bgcolor=ft.Colors.with_opacity(
                    tokens.OPACITY_CONTAINER, ft.Colors.PRIMARY
                ),
                tooltip=f"Colab Connected: {state.active_session_name} ({state.session_hardware}) - Tap for status",
                margin=ft.Margin(
                    tokens.SPACE_NONE,
                    tokens.SPACE_NONE,
                    tokens.SPACE_XS,
                    tokens.SPACE_NONE,
                ),
                on_click=lambda _: __import__(
                    "components.colab_status_dialog"
                ).colab_status_dialog.show_colab_status_dialog(
                    page, services.colab, state.active_session_name
                ),
            )
        else:
            colab_indicator = ft.Container(
                content=ft.Row(
                    [
                        ft.Icon(
                            ft.Icons.CLOUD_OFF_ROUNDED,
                            size=tokens.ICON_SM,
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
                    tokens.SPACE_SM,
                    tokens.SPACE_XXS,
                    tokens.SPACE_SM,
                    tokens.SPACE_XXS,
                ),
                border_radius=tokens.RADIUS_SM,
                border=ft.Border.all(
                    tokens.DIVIDER_THICKNESS,
                    ft.Colors.with_opacity(tokens.OPACITY_BORDER, ft.Colors.ON_SURFACE),
                ),
                tooltip="Colab Disconnected - Click to connect",
                margin=ft.Margin(
                    tokens.SPACE_NONE,
                    tokens.SPACE_NONE,
                    tokens.SPACE_XS,
                    tokens.SPACE_NONE,
                ),
                on_click=lambda _: (
                    page.run_task(_connect_colab_header) if page else None
                ),
            )

        ai_busy = state.is_analyzing or state.autopilot_running
        ai_busy_chip = ft.Container(
            content=ft.Row(
                [
                    ft.ProgressRing(
                        width=tokens.PROGRESS_RING_XS,
                        height=tokens.PROGRESS_RING_XS,
                        stroke_width=tokens.PROGRESS_RING_STROKE_THIN,
                    ),
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
                tokens.SPACE_SM,
                tokens.SPACE_XXS,
                tokens.SPACE_SM,
                tokens.SPACE_XXS,
            ),
            border_radius=tokens.RADIUS_SM,
            bgcolor=ft.Colors.with_opacity(tokens.OPACITY_CONTAINER, ft.Colors.PRIMARY),
            tooltip="An AI task is running - results appear on the Analysis tab",
            margin=ft.Margin(
                tokens.SPACE_NONE,
                tokens.SPACE_NONE,
                tokens.SPACE_XS,
                tokens.SPACE_NONE,
            ),
            visible=ai_busy,
        )

        top_bar = ft.Container(
            content=ft.Row(
                controls=[
                    page_tag,
                    ft.Row(
                        controls=[
                            ai_busy_chip,
                            colab_indicator,
                            theme_btn,
                            badge_container,
                        ],
                        spacing=tokens.SPACE_XS,
                        alignment=ft.MainAxisAlignment.END,
                    ),
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            padding=ft.Padding(
                tokens.SPACE_LG,
                tokens.SPACE_SM,
                tokens.SPACE_LG,
                tokens.SPACE_SM,
            ),
        )

    # ── Bottom Bar Assembly ──────────────────────────────────────
    bottom_bar = None
    if show_dashboard:

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
        bottom_bar = ft.NavigationBar(
            destinations=destinations,
            selected_index=state.current_tab,
            on_change=_on_tab_change,
            bgcolor=ft.Colors.SURFACE,
            indicator_color=ft.Colors.with_opacity(
                tokens.OPACITY_CONTAINER, ft.Colors.PRIMARY
            ),
            label_behavior=ft.NavigationBarLabelBehavior.ALWAYS_SHOW,
        )

    # ── Screen switching ─────────────────────────────────────────
    if not state.app_ready:
        screen = ft.Container(
            content=ft.Column(
                [
                    ft.Image(
                        src="icon.png",
                        width=tokens.ICON_CONTAINER_LG,
                        height=tokens.ICON_CONTAINER_LG,
                        fit=ft.BoxFit.CONTAIN,
                    ),
                    ft.Container(height=tokens.SPACE_XXL),
                    ft.ProgressRing(
                        width=tokens.PROGRESS_RING_LG,
                        height=tokens.PROGRESS_RING_LG,
                        stroke_width=tokens.PROGRESS_RING_STROKE_NORMAL,
                    ),
                ],
                alignment=ft.MainAxisAlignment.CENTER,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            expand=True,
            alignment=ft.Alignment.CENTER,
        )
    elif not state.onboarding_done or not state.is_authenticated:
        from screens.onboarding import OnboardingScreen

        screen = OnboardingScreen(key=ft.ValueKey("onboarding"))
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

    layout_controls = [offline_banner]
    if top_bar is not None:
        layout_controls.append(top_bar)
    layout_controls.append(ft.SafeArea(content=screen, expand=True))
    if bottom_bar is not None:
        layout_controls.append(bottom_bar)

    return ft.Column(
        controls=layout_controls,
        expand=True,
        spacing=tokens.SPACE_NONE,
    )
