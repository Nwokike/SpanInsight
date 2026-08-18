"""Debug / Live Activity Terminal section — ktvplayer style."""

from __future__ import annotations

import flet as ft

from core import theme, tokens
from core.logger_handler import MemoryLogHandler
from core.styles import glass_card, section_header


def build_logs_dialog(page: ft.Page) -> ft.AlertDialog:
    """Build the live activity terminal dialog showing captured application logs."""
    logs = MemoryLogHandler.get_logs()
    logs_str = "\n".join(logs) if logs else "No activity logged yet."

    log_text = ft.Text(
        value=logs_str,
        font_family="Courier New",
        size=11,
        color="#A6E22E",
        selectable=True,
    )

    async def _copy(e=None):
        try:
            await page.set_clipboard_async(log_text.value)
            from core.utils import show_snack

            show_snack(page, "Logs copied to clipboard", success=True)
        except Exception:
            pass

    def _clear(e=None):
        MemoryLogHandler.clear_logs()
        log_text.value = "Logs cleared."
        try:
            page.update()
        except Exception:
            pass

    return ft.AlertDialog(
        title=ft.Row(
            controls=[
                ft.Icon(
                    ft.Icons.TERMINAL_ROUNDED,
                    size=22,
                    color=theme.PRIMARY,
                ),
                ft.Text(
                    "Live Activity Terminal",
                    size=tokens.FONT_LG,
                    weight=ft.FontWeight.W_500,
                ),
            ],
            spacing=8,
        ),
        content=ft.Container(
            content=ft.Column(
                controls=[
                    ft.Text(
                        "Real-time log of background tasks, network requests, and events.",
                        size=tokens.FONT_XS,
                        color=ft.Colors.ON_SURFACE_VARIANT,
                    ),
                    ft.Container(
                        content=ft.Column(
                            controls=[log_text],
                            scroll=ft.ScrollMode.AUTO,
                        ),
                        bgcolor="#0D0D0D",
                        border=ft.Border.all(
                            1, ft.Colors.with_opacity(0.15, ft.Colors.WHITE)
                        ),
                        border_radius=tokens.RADIUS_MD,
                        padding=tokens.SPACE_MD,
                        expand=True,
                    ),
                ],
                spacing=tokens.SPACE_SM,
            ),
            width=480,
            height=400,
        ),
        actions=[
            ft.TextButton(
                "Copy",
                icon=ft.Icons.COPY_ROUNDED,
                on_click=lambda e: page.run_task(_copy),
            ),
            ft.TextButton(
                "Clear",
                icon=ft.Icons.DELETE_SWEEP_ROUNDED,
                on_click=_clear,
            ),
            ft.TextButton("Close", on_click=lambda e: page.pop_dialog()),
        ],
        actions_alignment=ft.MainAxisAlignment.END,
    )


def build_debug_section(page: ft.Page) -> list[ft.Control]:
    """Activity Terminal setting card with live memory counter."""
    logs_count = len(MemoryLogHandler.get_logs())

    def _open_terminal(e=None):
        if page:
            page.show_dialog(build_logs_dialog(page))

    return [
        section_header("Development & Debug"),
        glass_card(
            ft.Row(
                controls=[
                    ft.Icon(
                        ft.Icons.TERMINAL_ROUNDED,
                        size=tokens.ICON_LG,
                        color=theme.PRIMARY,
                    ),
                    ft.Column(
                        controls=[
                            ft.Text(
                                "Live Activity Terminal",
                                size=tokens.FONT_MD,
                                weight=ft.FontWeight.W_500,
                            ),
                            ft.Text(
                                f"{logs_count} entries in memory",
                                size=tokens.FONT_XS,
                                color=ft.Colors.ON_SURFACE_VARIANT,
                            ),
                        ],
                        spacing=tokens.SPACE_XXS,
                        expand=True,
                    ),
                    ft.FilledTonalButton(
                        content=ft.Text("Open"),
                        icon=ft.Icons.TERMINAL_ROUNDED,
                        on_click=_open_terminal,
                    ),
                ],
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=tokens.SPACE_LG,
            ),
        ),
    ]
