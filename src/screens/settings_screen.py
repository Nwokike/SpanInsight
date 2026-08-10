"""Settings view v2 — Cloud account, hardware defaults, debug terminal, credits.

Evolved from v1: removes workspace/project settings,
adds Cloud account management, hardware picker, and debug terminal.
"""

from __future__ import annotations

import logging

import flet as ft

from core import theme, tokens
from core.constants import (
    APP_VERSION,
    GPU_OPTIONS,
    STORAGE_DEFAULT_GPU,
    STORAGE_DEFAULT_TIMEOUT,
    STORAGE_DEFAULT_TPU,
    STORAGE_KEEP_ALIVE,
    STORAGE_THEME,
    STORAGE_UUID,
    TIMEOUT_OPTIONS,
    TPU_OPTIONS,
)
from core.styles import glass_card, section_header, setting_tile
from state import AppStateCtx
from state.controller_ctx import ControllerMethodsCtx
from state.service_ctx import ServiceCtx

logger = logging.getLogger(__name__)


def _get_cli_version():
    try:
        from colab_cli.auto_update import get_app_version as _get_cli_ver

        return _get_cli_ver()
    except Exception:
        return "unknown"


@ft.component
def SettingsScreen() -> ft.Control:
    """Build the Settings tab view."""
    page = ft.context.page
    state = ft.use_context(AppStateCtx)
    services = ft.use_context(ServiceCtx)
    ft.use_context(ControllerMethodsCtx)

    terminal_output, set_terminal_output = ft.use_state("")
    terminal_visible, set_terminal_visible = ft.use_state(False)
    cli_version = ft.use_memo(_get_cli_version, [])

    # ── Helpers ──────────────────────────────────────────────────
    def _show_credits():
        from components.credit_badge import show_credits_dialog

        show_credits_dialog(page, services.credits)

    async def on_launch_privacy(e):
        await ft.UrlLauncher().launch_url("https://spaninsight.com/privacy.html")

    async def on_launch_terms(e):
        await ft.UrlLauncher().launch_url("https://spaninsight.com/terms.html")

    # ── Theme ───────────────────────────────────────────────────
    async def on_theme_changed(e):
        mode = e.control.value
        if mode == "dark":
            page.theme_mode = ft.ThemeMode.DARK
        elif mode == "light":
            page.theme_mode = ft.ThemeMode.LIGHT
        else:
            page.theme_mode = ft.ThemeMode.SYSTEM
        state.theme_mode = page.theme_mode
        if services.storage:
            await services.storage.set(STORAGE_THEME, mode)
        page.update()

    current_theme = "light"
    if page.theme_mode == ft.ThemeMode.DARK:
        current_theme = "dark"
    elif page.theme_mode == ft.ThemeMode.SYSTEM:
        current_theme = "system"

    # ── Hardware defaults ───────────────────────────────────────
    async def _on_gpu_change(e):
        state.default_gpu = e.control.value or ""
        if services.storage:
            await services.storage.set(STORAGE_DEFAULT_GPU, state.default_gpu)

    async def _on_tpu_change(e):
        state.default_tpu = e.control.value or ""
        if services.storage:
            await services.storage.set(STORAGE_DEFAULT_TPU, state.default_tpu)

    async def _on_timeout_change(e):
        state.default_timeout = int(e.control.value)
        if services.storage:
            await services.storage.set(STORAGE_DEFAULT_TIMEOUT, state.default_timeout)

    async def _on_keep_alive_change(e):
        state.keep_alive_enabled = e.control.value
        if services.storage:
            await services.storage.set(STORAGE_KEEP_ALIVE, state.keep_alive_enabled)

    # ── Colab account ───────────────────────────────────────────
    async def _sign_out(e):
        if services.colab:
            await services.colab.clear_token()
        state.is_authenticated = False
        state.colab_authenticated = False
        state.auth_email = ""
        state.colab_connected = False
        state.active_sessions = []
        page.open(
            ft.SnackBar(
                content=ft.Text("Signed out from Google"),
                duration=2000,
            )
        )

    async def _check_auth(e):
        if not services.colab:
            return
        result = await services.colab.check_auth()
        if result.get("authenticated"):
            state.is_authenticated = True
            state.auth_email = result.get("email", "")
            page.open(
                ft.SnackBar(
                    content=ft.Text(f"✓ Authenticated as {state.auth_email}"),
                    duration=3000,
                )
            )
        else:
            state.is_authenticated = False
            state.auth_email = ""
            page.open(
                ft.SnackBar(
                    content=ft.Text("Not authenticated — sign in from onboarding"),
                    duration=3000,
                )
            )

    # ── Clear data ──────────────────────────────────────────────
    async def on_clear_data(e):
        def close_dialog(confirmed):
            async def _close(ev):
                page.close(dialog)
                if confirmed and services.storage:
                    for key in [
                        STORAGE_UUID,
                        STORAGE_THEME,
                        STORAGE_DEFAULT_GPU,
                        STORAGE_DEFAULT_TPU,
                    ]:
                        try:
                            await services.storage.delete(key)
                        except Exception:
                            pass
                    state.user_uuid = ""
                    page.open(
                        ft.SnackBar(
                            content=ft.Text("Local settings cleared."),
                            duration=2000,
                        )
                    )

            return _close

        dialog = ft.AlertDialog(
            title=ft.Text("Clear All Local Data?"),
            content=ft.Text(
                "This will delete saved settings and preferences. "
                "Your Colab sessions and Google account will not be affected."
            ),
            actions=[
                ft.TextButton("Cancel", on_click=close_dialog(False)),
                ft.FilledButton(
                    "Clear",
                    style=ft.ButtonStyle(bgcolor=theme.ERROR),
                    on_click=close_dialog(True),
                ),
            ],
        )
        page.open(dialog)

    # ── Debug terminal ──────────────────────────────────────────
    async def _run_debug(e):
        if not services.colab or not state.active_session_name:
            set_terminal_output("No active session. Start one from the Notebook tab.")
            set_terminal_visible(True)
            return

        set_terminal_output("Running diagnostics...")
        set_terminal_visible(True)

        try:
            code = (
                "import sys, os\\n"
                "print(f'Python: {sys.version}')\\n"
                "print(f'CWD: {os.getcwd()}')\\n"
                "print(f'Files: {os.listdir(\"/content\")[:10]}')\\n"
                "try:\\n"
                "    import torch; print(f'PyTorch: {torch.__version__}, CUDA: {torch.cuda.is_available()}')\\n"
                "except: print('PyTorch: not installed')\\n"
                "try:\\n"
                "    import tensorflow as tf; print(f'TF: {tf.__version__}')\\n"
                "except: print('TF: not installed')"
            )
            outputs = await services.colab.exec_code(
                code, state.active_session_name, timeout=15.0
            )
            text_parts = []
            for o in outputs:
                if o.get("output_type") == "stream":
                    text_parts.append(o.get("text", ""))
                elif o.get("output_type") == "error":
                    text_parts.append(f"ERROR: {o.get('ename')}: {o.get('evalue')}")

            res = "".join(text_parts) or "No output"
            set_terminal_output(res)
        except Exception as ex:
            set_terminal_output(f"Error: {ex}")

    # ── Banner ad helper ────────────────────────────────────────
    def _ad():
        if page.platform in (ft.PagePlatform.ANDROID, ft.PagePlatform.IOS):
            try:
                import flet_ads as fta

                return ft.Container(
                    content=fta.BannerAd(
                        unit_id="ca-app-pub-5679949845754640/5628404223",
                        width=320,
                        height=50,
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
            except Exception:
                pass
        return ft.Container()

    # ── Build layout ────────────────────────────────────────────
    return ft.Column(
        controls=[
            ft.Container(
                content=ft.Text(
                    "Settings", weight=ft.FontWeight.W_600, size=tokens.FONT_XL
                ),
                padding=ft.Padding(
                    tokens.SPACE_LG, tokens.SPACE_MD, tokens.SPACE_LG, tokens.SPACE_MD
                ),
            ),
            # ── Colab Account ─────────────────────────────────────
            section_header("Google Account"),
            setting_tile(
                icon=ft.Icons.ACCOUNT_CIRCLE_ROUNDED,
                title=state.auth_email or "Not signed in",
                subtitle="Colab OAuth2 — tap to verify"
                if state.is_authenticated
                else "Sign in from onboarding",
                on_click=lambda e: page.run_task(_check_auth, e),
            ),
            *(
                [
                    setting_tile(
                        icon=ft.Icons.LOGOUT_ROUNDED,
                        title="Sign Out",
                        subtitle="Disconnect Google account",
                        on_click=lambda e: page.run_task(_sign_out, e),
                    )
                ]
                if state.is_authenticated
                else []
            ),
            # ── Hardware Defaults ─────────────────────────────────
            section_header("Hardware Defaults"),
            glass_card(
                ft.Column(
                    controls=[
                        ft.Row(
                            controls=[
                                ft.Icon(
                                    ft.Icons.DEVELOPER_BOARD_ROUNDED,
                                    size=tokens.ICON_LG,
                                    color=ft.Colors.ON_SURFACE_VARIANT,
                                ),
                                ft.Column(
                                    [
                                        ft.Text(
                                            "Default GPU",
                                            size=tokens.FONT_MD,
                                            weight=ft.FontWeight.W_500,
                                        ),
                                        ft.Text(
                                            "Pre-selected when creating sessions",
                                            size=tokens.FONT_XS,
                                            color=ft.Colors.ON_SURFACE_VARIANT,
                                            italic=True,
                                        ),
                                    ],
                                    spacing=tokens.SPACE_XXS,
                                    expand=True,
                                ),
                                ft.Dropdown(
                                    value=state.default_gpu or "",
                                    options=[
                                        ft.dropdown.Option(k, v) for k, v in GPU_OPTIONS
                                    ],
                                    width=130,
                                    border_radius=tokens.RADIUS_MD,
                                    text_size=tokens.FONT_SM,
                                    on_select=lambda e: page.run_task(
                                        _on_gpu_change, e
                                    ),
                                ),
                            ],
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                            spacing=tokens.SPACE_LG,
                        ),
                        ft.Divider(height=tokens.SPACE_SM),
                        ft.Row(
                            controls=[
                                ft.Icon(
                                    ft.Icons.BOLT_ROUNDED,
                                    size=tokens.ICON_LG,
                                    color=ft.Colors.ON_SURFACE_VARIANT,
                                ),
                                ft.Column(
                                    [
                                        ft.Text(
                                            "Default TPU",
                                            size=tokens.FONT_MD,
                                            weight=ft.FontWeight.W_500,
                                        ),
                                        ft.Text(
                                            "Pre-selected when creating sessions",
                                            size=tokens.FONT_XS,
                                            color=ft.Colors.ON_SURFACE_VARIANT,
                                            italic=True,
                                        ),
                                    ],
                                    spacing=tokens.SPACE_XXS,
                                    expand=True,
                                ),
                                ft.Dropdown(
                                    value=state.default_tpu or "",
                                    options=[
                                        ft.dropdown.Option(k, v) for k, v in TPU_OPTIONS
                                    ],
                                    width=130,
                                    border_radius=tokens.RADIUS_MD,
                                    text_size=tokens.FONT_SM,
                                    on_select=lambda e: page.run_task(
                                        _on_tpu_change, e
                                    ),
                                ),
                            ],
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                            spacing=tokens.SPACE_LG,
                        ),
                    ],
                ),
            ),
            # ── Execution ─────────────────────────────────────────
            section_header("Execution"),
            glass_card(
                ft.Column(
                    controls=[
                        ft.Row(
                            controls=[
                                ft.Icon(
                                    ft.Icons.TIMER_ROUNDED,
                                    size=tokens.ICON_LG,
                                    color=ft.Colors.ON_SURFACE_VARIANT,
                                ),
                                ft.Column(
                                    [
                                        ft.Text(
                                            "Default Timeout",
                                            size=tokens.FONT_MD,
                                            weight=ft.FontWeight.W_500,
                                        ),
                                        ft.Text(
                                            "Max wait for code execution",
                                            size=tokens.FONT_XS,
                                            color=ft.Colors.ON_SURFACE_VARIANT,
                                            italic=True,
                                        ),
                                    ],
                                    spacing=tokens.SPACE_XXS,
                                    expand=True,
                                ),
                                ft.Dropdown(
                                    value=str(state.default_timeout),
                                    options=[
                                        ft.dropdown.Option(str(t), f"{t}s")
                                        for t in TIMEOUT_OPTIONS
                                    ],
                                    width=90,
                                    border_radius=tokens.RADIUS_MD,
                                    text_size=tokens.FONT_SM,
                                    on_select=lambda e: page.run_task(
                                        _on_timeout_change, e
                                    ),
                                ),
                            ],
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                            spacing=tokens.SPACE_LG,
                        ),
                        ft.Divider(height=tokens.SPACE_SM),
                        ft.Row(
                            controls=[
                                ft.Column(
                                    [
                                        ft.Text(
                                            "Keep-Alive",
                                            size=tokens.FONT_MD,
                                            weight=ft.FontWeight.W_500,
                                        ),
                                        ft.Text(
                                            "Prevent sessions from idling out",
                                            size=tokens.FONT_XS,
                                            color=ft.Colors.ON_SURFACE_VARIANT,
                                            italic=True,
                                        ),
                                    ],
                                    spacing=tokens.SPACE_XXS,
                                    expand=True,
                                ),
                                ft.Switch(
                                    value=state.keep_alive_enabled,
                                    on_change=lambda e: page.run_task(
                                        _on_keep_alive_change, e
                                    ),
                                ),
                            ],
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                    ],
                ),
            ),
            # ── AI Credits ────────────────────────────────────────
            _ad(),
            section_header("AI Credits"),
            setting_tile(
                icon=ft.Icons.BOLT_ROUNDED,
                title="Daily Credits",
                subtitle=f"{state.credits_remaining} remaining today",
                on_click=lambda e: _show_credits(),
            ),
            # ── Appearance ────────────────────────────────────────
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
                padding=ft.Padding(tokens.SPACE_LG, 14, tokens.SPACE_LG, 14),
            ),
            # ── Debug Terminal ────────────────────────────────────
            section_header("Debug"),
            glass_card(
                ft.Column(
                    controls=[
                        ft.Row(
                            controls=[
                                ft.Icon(
                                    ft.Icons.TERMINAL_ROUNDED,
                                    size=tokens.ICON_LG,
                                    color=ft.Colors.ON_SURFACE_VARIANT,
                                ),
                                ft.Column(
                                    [
                                        ft.Text(
                                            "Debug Terminal",
                                            size=tokens.FONT_MD,
                                            weight=ft.FontWeight.W_500,
                                        ),
                                        ft.Text(
                                            "Run diagnostics on the active Colab session",
                                            size=tokens.FONT_XS,
                                            color=ft.Colors.ON_SURFACE_VARIANT,
                                            italic=True,
                                        ),
                                    ],
                                    spacing=tokens.SPACE_XXS,
                                    expand=True,
                                ),
                                ft.FilledTonalButton(
                                    content=ft.Text("Run"),
                                    icon=ft.Icons.PLAY_ARROW_ROUNDED,
                                    on_click=lambda e: page.run_task(_run_debug, e),
                                ),
                            ],
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                            spacing=tokens.SPACE_LG,
                        ),
                        ft.Text(
                            value=terminal_output,
                            size=tokens.FONT_XS,
                            color=ft.Colors.ON_SURFACE_VARIANT,
                            selectable=True,
                            visible=terminal_visible,
                            font_family="monospace",
                        ),
                    ],
                ),
            ),
            # ── Data Management ───────────────────────────────────
            section_header("Data Management"),
            setting_tile(
                icon=ft.Icons.DELETE_OUTLINE_ROUNDED,
                title="Clear Local Settings",
                subtitle="Reset preferences (Colab account unaffected)",
                on_click=lambda e: page.run_task(on_clear_data, e),
            ),
            # ── About ────────────────────────────────────────────
            _ad(),
            section_header("About"),
            glass_card(
                ft.Column(
                    controls=[
                        ft.Container(
                            content=ft.Image(
                                src="icon.png",
                                width=96,
                                height=96,
                                fit=ft.BoxFit.CONTAIN,
                            ),
                            alignment=ft.Alignment.CENTER,
                            margin=ft.Margin(0, 0, 0, tokens.SPACE_SM),
                        ),
                        ft.Text(
                            "Ready Autonomous Data Intelligence for Everyone",
                            size=tokens.FONT_SM,
                            color=ft.Colors.ON_SURFACE_VARIANT,
                            text_align=ft.TextAlign.CENTER,
                        ),
                        ft.Container(height=tokens.SPACE_SM),
                        ft.Row(
                            [
                                ft.Text("Version", size=tokens.FONT_SM),
                                ft.Text(
                                    f"v{APP_VERSION}",
                                    size=tokens.FONT_SM,
                                    color=ft.Colors.ON_SURFACE_VARIANT,
                                ),
                            ],
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        ),
                        ft.Row(
                            [
                                ft.Text("Powered by", size=tokens.FONT_SM),
                                ft.Text(
                                    f"Google Colab (CLI v{cli_version})",
                                    size=tokens.FONT_SM,
                                    color=ft.Colors.ON_SURFACE_VARIANT,
                                ),
                            ],
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        ),
                        ft.Divider(
                            height=1,
                            color=ft.Colors.with_opacity(0.04, ft.Colors.ON_SURFACE),
                        ),
                        ft.Row(
                            [
                                ft.TextButton(
                                    "Privacy Policy",
                                    icon=ft.Icons.PRIVACY_TIP_ROUNDED,
                                    style=ft.ButtonStyle(color=theme.PRIMARY),
                                    on_click=on_launch_privacy,
                                ),
                                ft.TextButton(
                                    "Terms of Service",
                                    icon=ft.Icons.GAVEL_ROUNDED,
                                    style=ft.ButtonStyle(color=theme.PRIMARY),
                                    on_click=on_launch_terms,
                                ),
                            ],
                            alignment=ft.MainAxisAlignment.SPACE_EVENLY,
                        ),
                    ],
                    spacing=tokens.SPACE_XS,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                ),
            ),
            # ── Pro tease ─────────────────────────────────────────
            ft.Container(
                content=ft.Row(
                    controls=[
                        ft.Icon(
                            ft.Icons.WORKSPACE_PREMIUM_ROUNDED,
                            size=tokens.ICON_LG,
                            color=ft.Colors.with_opacity(0.4, theme.PRIMARY),
                        ),
                        ft.Column(
                            [
                                ft.Text(
                                    "SpanInsight Pro",
                                    size=tokens.FONT_MD,
                                    weight=ft.FontWeight.W_500,
                                    color=ft.Colors.with_opacity(
                                        0.5, ft.Colors.ON_SURFACE
                                    ),
                                ),
                                ft.Text(
                                    "Zero ads • Unlimited credits • Priority support",
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
                                tokens.SPACE_SM,
                                tokens.SPACE_XXS,
                                tokens.SPACE_SM,
                                tokens.SPACE_XXS,
                            ),
                            border_radius=tokens.RADIUS_SM,
                            bgcolor=ft.Colors.with_opacity(0.1, theme.ACCENT),
                        ),
                    ],
                    spacing=tokens.SPACE_LG,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                padding=ft.Padding(tokens.SPACE_LG, 14, tokens.SPACE_LG, 14),
                opacity=0.6,
            ),
            ft.Container(height=80),
        ],
        scroll=ft.ScrollMode.AUTO,
        expand=True,
        spacing=tokens.SPACE_XXS,
    )
