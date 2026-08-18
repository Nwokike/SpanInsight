"""SettingsScreen — Modular Cloud account, hardware defaults, debug terminal, and preferences."""

from __future__ import annotations

import logging

import flet as ft

from core import theme, tokens
from core.constants import (
    STORAGE_DEFAULT_GPU,
    STORAGE_DEFAULT_TIMEOUT,
    STORAGE_DEFAULT_TPU,
    STORAGE_KEEP_ALIVE,
    STORAGE_THEME,
    STORAGE_UUID,
)
from core.styles import section_header, setting_tile
from screens.settings.about_section import build_about_section
from screens.settings.appearance_section import build_appearance_section
from screens.settings.auth_section import build_auth_section
from screens.settings.data_section import build_data_section
from screens.settings.debug_section import build_debug_section
from screens.settings.hardware_section import build_hardware_section
from state import AppStateCtx
from state.controller_ctx import ControllerMethodsCtx
from state.service_ctx import ServiceCtx

logger = logging.getLogger("SettingsScreen")


def _get_cli_version():
    try:
        from colab_cli.auto_update import get_app_version as _get_cli_ver

        return _get_cli_ver()
    except Exception:
        return "unknown"


@ft.component
def SettingsScreen() -> ft.Control:
    """Build the Settings tab view assembling modular sections."""
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

    async def on_launch_privacy(e=None):
        from core.constants import PRIVACY_POLICY_URL

        await ft.UrlLauncher().launch_url(PRIVACY_POLICY_URL)

    async def on_launch_terms(e=None):
        from core.constants import TERMS_OF_SERVICE_URL

        await ft.UrlLauncher().launch_url(TERMS_OF_SERVICE_URL)

    # ── Theme ───────────────────────────────────────────────────
    async def on_theme_changed(mode: str):
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

    current_theme = "system"
    if page.theme_mode == ft.ThemeMode.DARK:
        current_theme = "dark"
    elif page.theme_mode == ft.ThemeMode.LIGHT:
        current_theme = "light"

    # ── Hardware defaults ───────────────────────────────────────
    async def _on_accelerator_change(e):
        val = e.control.value or ""
        if val in ("v5e1", "v6e1"):
            state.default_tpu = val
            state.default_gpu = ""
        else:
            state.default_gpu = val
            state.default_tpu = ""
        if services.storage:
            await services.storage.set(STORAGE_DEFAULT_GPU, state.default_gpu)
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
    async def _sign_out(e=None):
        from core.constants import STORAGE_ONBOARDING_DONE

        if services.colab:
            await services.colab.clear_token()
        if services.storage:
            await services.storage.delete(STORAGE_ONBOARDING_DONE)
        state.onboarding_done = False
        state.is_authenticated = False
        state.colab_authenticated = False
        state.auth_email = ""
        state.colab_connected = False
        state.active_session_name = ""
        state.active_sessions = []
        state.current_tab = 0
        if page:
            from core.utils import show_snack

            show_snack(page, "Signed out successfully", duration=2000)
            page.update()

    async def _check_auth(e=None):
        if not services.colab:
            return
        if page:
            from core.utils import show_snack

            show_snack(page, "Checking Google account…", duration=1500)
        try:
            result = await services.colab.check_auth()
        except Exception as ex:
            logger.warning("Auth check failed: %s", ex)
            if page:
                from core.utils import show_snack

                show_snack(page, f"Auth check failed: {ex}", error=True, duration=3000)
            return
        if result.get("authenticated"):
            state.is_authenticated = True
            state.auth_email = result.get("email", "")
            if page:
                from core.utils import show_snack

                show_snack(
                    page,
                    f"✓ Authenticated as {state.auth_email}",
                    success=True,
                    duration=3000,
                )
        else:
            state.is_authenticated = False
            state.auth_email = ""
            if page:
                from core.utils import show_snack

                show_snack(
                    page,
                    "Not authenticated — sign in from onboarding",
                    duration=3000,
                )

    # ── Clear data ──────────────────────────────────────────────
    async def on_clear_data(e=None):
        def close_dialog(confirmed):
            async def _close(ev):
                page.pop_dialog()
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
                    from core.utils import show_snack

                    show_snack(page, "Local settings cleared.", duration=2000)

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
        page.show_dialog(dialog)

    # ── Debug terminal ──────────────────────────────────────────
    async def _run_debug(e=None):
        if not services.colab or not state.active_session_name:
            set_terminal_output("No active session. Start one from the Notebook tab.")
            set_terminal_visible(True)
            return

        set_terminal_output("Running diagnostics...")
        set_terminal_visible(True)

        try:
            code = (
                "import sys, os\n"
                "print(f'Python: {sys.version}')\n"
                "print(f'CWD: {os.getcwd()}')\n"
                "print(f'Files: {os.listdir(\"/content\")[:10]}')\n"
                "try:\n"
                "    import torch; print(f'PyTorch: {torch.__version__}, CUDA: {torch.cuda.is_available()}')\n"
                "except: print('PyTorch: not installed')\n"
                "try:\n"
                "    import tensorflow as tf; print(f'TF: {tf.__version__}')\n"
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
        if page and page.platform in (ft.PagePlatform.ANDROID, ft.PagePlatform.IOS):
            try:
                from core.utils import get_banner_ad

                return ft.Container(
                    content=get_banner_ad(),
                    alignment=ft.Alignment.CENTER,
                    padding=tokens.SPACE_SM,
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

    # ── Assemble layout ─────────────────────────────────────────
    controls = [
        ft.Container(
            content=ft.Text(
                "Settings", weight=ft.FontWeight.W_600, size=tokens.FONT_XL
            ),
            padding=ft.Padding(
                tokens.SPACE_LG, tokens.SPACE_MD, tokens.SPACE_LG, tokens.SPACE_MD
            ),
        ),
    ]
    controls.extend(
        build_appearance_section(
            current_theme, lambda mode: page.run_task(on_theme_changed, mode)
        )
    )
    controls.extend(
        build_auth_section(
            state,
            lambda e: page.run_task(_check_auth, e),
            lambda e: page.run_task(_sign_out, e),
        )
    )
    controls.extend(
        build_hardware_section(
            state,
            lambda e: page.run_task(_on_accelerator_change, e),
            lambda e: page.run_task(_on_timeout_change, e),
            lambda e: page.run_task(_on_keep_alive_change, e),
        )
    )
    controls.append(_ad())
    controls.append(section_header("AI Credits"))
    controls.append(
        setting_tile(
            icon=ft.Icons.BOLT_ROUNDED,
            title="Daily Credits",
            subtitle=f"{state.credits_remaining} remaining today",
            on_click=lambda e: _show_credits(),
        )
    )
    controls.extend(
        build_debug_section(
            terminal_output, terminal_visible, lambda e: page.run_task(_run_debug, e)
        )
    )
    controls.extend(build_data_section(lambda e: page.run_task(on_clear_data, e)))
    controls.append(_ad())
    controls.extend(
        build_about_section(cli_version, on_launch_privacy, on_launch_terms)
    )
    controls.append(ft.Container(height=80))

    return ft.Column(
        controls=controls,
        scroll=ft.ScrollMode.AUTO,
        expand=True,
        spacing=tokens.SPACE_XXS,
    )
