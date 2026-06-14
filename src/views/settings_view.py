"""Settings view — project-centric workspace and device config."""

from __future__ import annotations

import logging
import flet as ft

from core import theme, tokens, utils
from core.state import state
from core.constants import (
    STORAGE_THEME,
    STORAGE_UUID,
)
from core.styles import section_header, setting_tile
from components.brand_header import build_brand_header

logger = logging.getLogger(__name__)


def build_settings_view(
    page: ft.Page,
    credit_service,
    storage=None,
) -> ft.View:
    """Build the Settings tab view."""

    def show_dialog(dialog):
        page.show_dialog(dialog)

    async def close_dialog_helper(dialog):
        page.pop_dialog()

    def _show_credits():
        from components.credit_badge import show_credits_dialog

        show_credits_dialog(page, credit_service)

    # on_copy_uuid helper removed

    async def on_launch_privacy(e):
        await ft.UrlLauncher().launch_url("https://spaninsight.com/privacy.html")

    async def on_theme_changed(e):
        mode = e.control.value
        if mode == "dark":
            page.theme_mode = ft.ThemeMode.DARK
        elif mode == "light":
            page.theme_mode = ft.ThemeMode.LIGHT
        else:
            page.theme_mode = ft.ThemeMode.SYSTEM
        state.theme_mode = page.theme_mode

        # Persist
        if storage:
            await storage.set(STORAGE_THEME, mode)

        page.update()

    async def on_clear_data(e):
        def close_dialog(confirmed):
            async def _close(ev):
                await close_dialog_helper(dialog)
                if confirmed and storage:
                    # Wipe local workspaces, ID, and settings, but retain credits to prevent abuse
                    for key in [
                        STORAGE_UUID,
                        STORAGE_THEME,
                        "spaninsight_projects",
                        "spaninsight_active_project_id",
                    ]:
                        try:
                            await storage.delete(key)
                        except Exception:
                            pass
                    state.clear_data()
                    state.user_projects = {}
                    state.user_uuid = ""
                    page.snack_bar = ft.SnackBar(
                        content=ft.Text(
                            "All local workspaces & settings cleared. Restarting session..."
                        ),
                        duration=2000,
                    )
                    page.snack_bar.open = True
                    page.update()
                    await page.push_route("/onboarding")

            return _close

        dialog = ft.AlertDialog(
            title=ft.Text("Clear All Local Data?"),
            content=ft.Text(
                "This will permanently delete all your local project workspaces, "
                "AI analysis recipes, saved reports, survey forms, and settings. "
                "Your current credit balance will be retained.\n\n"
                "Are you sure you want to proceed?"
            ),
            actions=[
                ft.TextButton("Cancel", on_click=close_dialog(False)),
                ft.FilledButton(
                    "Clear Everything",
                    style=ft.ButtonStyle(bgcolor=theme.ERROR),
                    on_click=close_dialog(True),
                ),
            ],
        )
        show_dialog(dialog)

    # masked_uuid calculation removed

    # Project Workspace display details
    active_title = state.active_project.get("title", "My Workspace")
    is_local = state.active_project_id.startswith("loc_")
    display_pin = (
        "Local Only (Offline)" if is_local else f"PIN: {state.active_project_id}"
    )

    # Theme dropdown value
    current_theme = "light"
    if page.theme_mode == ft.ThemeMode.DARK:
        current_theme = "dark"
    elif page.theme_mode == ft.ThemeMode.SYSTEM:
        current_theme = "system"

    content = ft.Column(
        controls=[
            # ── Project Workspace Section ──────────────────────────────
            section_header("Active Workspace"),
            setting_tile(
                icon=ft.Icons.WORKSPACES_ROUNDED,
                title="Current Project",
                subtitle=active_title,
            ),
            setting_tile(
                icon=ft.Icons.LOCK_ROUNDED if is_local else ft.Icons.PEOPLE_ROUNDED,
                title="Connection Mode",
                subtitle=display_pin,
            ),
            # ── AI Credits Section ──────────────────────────────────────
            section_header("AI Credits"),
            setting_tile(
                icon=ft.Icons.BOLT_ROUNDED,
                title="Daily Credits",
                subtitle=f"{state.credits_remaining} remaining today",
                on_click=lambda e: _show_credits(),
            ),
            # Banner Ad (Mobile Only) - Middle Page
            (
                lambda: ft.Container(
                    content=ft.Column(
                        [
                            ft.Text(
                                "SPONSORED",
                                size=8,
                                weight=ft.FontWeight.W_700,
                                color=ft.Colors.ON_SURFACE_VARIANT,
                                style=ft.TextStyle(letter_spacing=1),
                            ),
                            utils.get_banner_ad(
                                unit_id="ca-app-pub-5679949845754640/5628404223",
                                width=320,
                                height=50,
                            ),
                        ],
                        horizontal_alignment="center",
                        spacing=4,
                    ),
                    alignment=ft.Alignment.CENTER,
                    padding=8,
                    border_radius=tokens.RADIUS_LG,
                    bgcolor=theme.GLASS_BG,
                    border=ft.Border.all(1, theme.GLASS_BORDER_COLOR),
                    margin=ft.Margin(
                        tokens.SPACE_LG,
                        tokens.SPACE_XS,
                        tokens.SPACE_LG,
                        tokens.SPACE_XS,
                    ),
                )
            )()
            if page.platform in (ft.PagePlatform.ANDROID, ft.PagePlatform.IOS)
            else ft.Container(),
            # ── Appearance Section ──────────────────────────────
            section_header("Appearance"),
            ft.Container(
                content=ft.Row(
                    controls=[
                        ft.Icon(
                            ft.Icons.PALETTE_ROUNDED,
                            size=tokens.ICON_LG,
                            color=ft.Colors.ON_SURFACE_VARIANT,
                        ),
                        ft.Text(
                            "Theme",
                            size=tokens.FONT_MD,
                            weight=ft.FontWeight.W_500,
                            expand=True,
                        ),
                        ft.Dropdown(
                            value=current_theme,
                            width=130,
                            options=[
                                ft.DropdownOption(key="light", text="Light"),
                                ft.DropdownOption(key="dark", text="Dark"),
                                ft.DropdownOption(key="system", text="System"),
                            ],
                            on_select=lambda e: page.run_task(on_theme_changed, e),
                            border_radius=tokens.RADIUS_MD,
                            text_size=tokens.FONT_SM,
                        ),
                    ],
                    spacing=tokens.SPACE_LG,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                padding=ft.Padding(
                    left=tokens.SPACE_LG,
                    right=tokens.SPACE_LG,
                    top=14,
                    bottom=14,
                ),
            ),
            # ── Data Section ────────────────────────────────────
            section_header("Data Management"),
            setting_tile(
                icon=ft.Icons.DELETE_OUTLINE_ROUNDED,
                title="Wipe Local Database & Projects",
                subtitle="Reset device ID, credits, and workspaces",
                on_click=lambda e: page.run_task(on_clear_data, e),
            ),
            # ── Pro Tier Tease ──────────────────────────────────
            section_header("Premium"),
            ft.Container(
                content=ft.Row(
                    controls=[
                        ft.Icon(
                            ft.Icons.WORKSPACE_PREMIUM_ROUNDED,
                            size=tokens.ICON_LG,
                            color=ft.Colors.with_opacity(0.4, theme.PRIMARY),
                        ),
                        ft.Column(
                            controls=[
                                ft.Text(
                                    "Spaninsight Pro",
                                    size=tokens.FONT_MD,
                                    weight=ft.FontWeight.W_500,
                                    color=ft.Colors.with_opacity(
                                        0.5, ft.Colors.ON_SURFACE
                                    ),
                                ),
                                ft.Text(
                                    "Zero ads \u2022 Priority AI \u2022 Unlimited credits",
                                    size=tokens.FONT_XS,
                                    color=ft.Colors.with_opacity(
                                        0.35, ft.Colors.ON_SURFACE
                                    ),
                                ),
                            ],
                            spacing=tokens.SPACE_XXS,
                            expand=True,
                        ),
                        ft.Container(
                            content=ft.Text(
                                "SOON",
                                size=tokens.FONT_XXS,
                                weight=ft.FontWeight.W_700,
                                color=theme.ACCENT,
                            ),
                            padding=ft.Padding(
                                left=tokens.SPACE_SM,
                                right=tokens.SPACE_SM,
                                top=tokens.SPACE_XXS,
                                bottom=tokens.SPACE_XXS,
                            ),
                            border_radius=tokens.RADIUS_SM,
                            bgcolor=ft.Colors.with_opacity(0.1, theme.ACCENT),
                        ),
                    ],
                    spacing=tokens.SPACE_LG,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                padding=ft.Padding(
                    left=tokens.SPACE_LG,
                    right=tokens.SPACE_LG,
                    top=14,
                    bottom=14,
                ),
                border_radius=tokens.RADIUS_MD,
                opacity=0.6,
            ),
            # ── About Section ──────────────────────────────────
            section_header("About"),
            setting_tile(
                icon=ft.Icons.INFO_OUTLINE_ROUNDED,
                title="Version",
                subtitle="Spaninsight v1.2.3",
            ),
            setting_tile(
                icon=ft.Icons.PRIVACY_TIP_OUTLINED,
                title="Privacy Policy",
                subtitle="Read our 100% privacy commitment",
                on_click=on_launch_privacy,
            ),
            # Banner Ad (Mobile Only)
            (
                lambda: ft.Container(
                    content=ft.Column(
                        [
                            ft.Text(
                                "SPONSORED",
                                size=8,
                                weight=ft.FontWeight.W_700,
                                color=ft.Colors.ON_SURFACE_VARIANT,
                                style=ft.TextStyle(letter_spacing=1),
                            ),
                            utils.get_banner_ad(
                                unit_id="ca-app-pub-5679949845754640/5628404223",
                                width=320,
                                height=50,
                            ),
                        ],
                        horizontal_alignment="center",
                        spacing=4,
                    ),
                    alignment=ft.Alignment.CENTER,
                    padding=8,
                    border_radius=tokens.RADIUS_LG,
                    bgcolor=theme.GLASS_BG,
                    border=ft.Border.all(1, theme.GLASS_BORDER_COLOR),
                    margin=ft.Margin(
                        tokens.SPACE_LG,
                        tokens.SPACE_MD,
                        tokens.SPACE_LG,
                        tokens.SPACE_MD,
                    ),
                )
            )()
            if page.platform in (ft.PagePlatform.ANDROID, ft.PagePlatform.IOS)
            else ft.Container(),
            ft.Container(height=tokens.SPACE_XL),
            ft.Container(
                content=build_brand_header(show_tagline=True, spacing_below=False),
                opacity=0.6,
            ),
            ft.Container(height=tokens.SPACE_XXXL),
        ],
        scroll=ft.ScrollMode.AUTO,
        expand=True,
        spacing=tokens.SPACE_XXS,
    )

    appbar = ft.AppBar(
        title=ft.Text("Settings", weight=ft.FontWeight.W_600, size=tokens.FONT_XL),
        center_title=False,
        bgcolor=ft.Colors.TRANSPARENT,
    )

    return ft.View(route="/settings", appbar=appbar, controls=[content], padding=0)
