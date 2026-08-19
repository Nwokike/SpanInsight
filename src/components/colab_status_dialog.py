"""Colab VM Status Dialog - Modern compact GUI system status inspection."""

from __future__ import annotations

import json
import logging

import flet as ft

from core import theme, tokens
from core.state import state

logger = logging.getLogger("ColabStatus")


def show_colab_status_dialog(page: ft.Page, colab, session_name: str):
    """Opens a compact, modern GUI modal displaying active Colab VM environment & runtime status."""
    if not page or not colab or not session_name:
        return

    progress_bar = ft.ProgressBar(
        width=tokens.DIALOG_WIDTH_SM,
        height=tokens.SPACE_NANO,
        color=theme.PRIMARY,
        bgcolor=ft.Colors.with_opacity(tokens.OPACITY_LIGHT, theme.PRIMARY),
    )

    details_column = ft.Column(
        controls=[
            ft.Container(
                content=ft.Row(
                    controls=[
                        ft.ProgressRing(
                            width=tokens.PROGRESS_RING_SM,
                            height=tokens.PROGRESS_RING_SM,
                            stroke_width=tokens.PROGRESS_RING_STROKE_THIN,
                        ),
                        ft.Text(
                            "Running diagnostics in VM…",
                            size=tokens.FONT_XS,
                            color=ft.Colors.ON_SURFACE_VARIANT,
                        ),
                    ],
                    spacing=tokens.SPACE_SM,
                    alignment=ft.MainAxisAlignment.CENTER,
                ),
                padding=tokens.SPACE_MD,
                alignment=ft.Alignment.CENTER,
            )
        ],
        spacing=tokens.SPACE_XS,
    )

    def _build_info_row(
        icon, label: str, value: str, badge_color=None, badge_text=None
    ) -> ft.Control:
        trailing_controls = []
        if badge_text:
            trailing_controls.append(
                ft.Container(
                    content=ft.Text(
                        badge_text,
                        size=tokens.FONT_XXS,
                        weight=ft.FontWeight.W_600,
                        color=badge_color or theme.PRIMARY,
                    ),
                    padding=ft.Padding(
                        tokens.SPACE_SM_XS,
                        tokens.SPACE_XXS,
                        tokens.SPACE_SM_XS,
                        tokens.SPACE_XXS,
                    ),
                    border_radius=tokens.RADIUS_XS,
                    bgcolor=ft.Colors.with_opacity(
                        tokens.OPACITY_CONTAINER, badge_color or theme.PRIMARY
                    ),
                )
            )

        trailing_controls.append(
            ft.Text(
                value,
                size=tokens.FONT_SM,
                weight=ft.FontWeight.W_500,
                color=ft.Colors.ON_SURFACE,
            )
        )

        return ft.Container(
            content=ft.Row(
                controls=[
                    ft.Icon(icon, size=tokens.ICON_SM, color=theme.PRIMARY),
                    ft.Text(
                        label,
                        size=tokens.FONT_SM,
                        color=ft.Colors.ON_SURFACE_VARIANT,
                        weight=ft.FontWeight.W_400,
                    ),
                    ft.Container(expand=True),
                    *trailing_controls,
                ],
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=tokens.SPACE_SM,
            ),
            padding=ft.Padding(
                tokens.SPACE_NONE, tokens.SPACE_XXS, tokens.SPACE_NONE, tokens.SPACE_XXS
            ),
        )

    def _render_gui_status(data: dict):
        progress_bar.visible = False
        python_ver = data.get("python", "Unknown")
        cwd = data.get("cwd", "/content")
        files = data.get("files", [])
        torch_ver = data.get("torch") or "Not installed"
        cuda_avail = data.get("cuda", False)
        cuda_text = "CUDA Available" if cuda_avail else "No GPU"
        cuda_color = theme.SUCCESS if cuda_avail else theme.WARNING
        tf_ver = data.get("tf") or "Not installed"

        file_chips = [
            ft.Container(
                content=ft.Text(
                    f, size=tokens.FONT_XXS, color=ft.Colors.ON_SURFACE_VARIANT
                ),
                padding=ft.Padding(
                    tokens.SPACE_SM_XS,
                    tokens.SPACE_XXS,
                    tokens.SPACE_SM_XS,
                    tokens.SPACE_XXS,
                ),
                border_radius=tokens.RADIUS_XS,
                bgcolor=ft.Colors.with_opacity(
                    tokens.OPACITY_MUTED, ft.Colors.ON_SURFACE
                ),
            )
            for f in files[:8]
        ]

        files_section = (
            ft.Column(
                controls=[
                    ft.Text(
                        "Files in /content",
                        size=tokens.FONT_XS,
                        color=ft.Colors.ON_SURFACE_VARIANT,
                        weight=ft.FontWeight.W_500,
                    ),
                    ft.Row(controls=file_chips, wrap=True, spacing=tokens.SPACE_XXS),
                ],
                spacing=tokens.SPACE_XS,
            )
            if files
            else ft.Container()
        )

        details_column.controls = [
            _build_info_row(ft.Icons.TERMINAL_ROUNDED, "Python Version", python_ver),
            _build_info_row(ft.Icons.FOLDER_OPEN_ROUNDED, "Working Directory", cwd),
            _build_info_row(
                ft.Icons.MEMORY_ROUNDED,
                "PyTorch",
                torch_ver,
                badge_color=cuda_color,
                badge_text=cuda_text,
            ),
            _build_info_row(ft.Icons.PSYCHOLOGY_ALT_ROUNDED, "TensorFlow", tf_ver),
            ft.Divider(
                height=tokens.SPACE_SM,
                color=ft.Colors.with_opacity(
                    tokens.OPACITY_SUBTLE, ft.Colors.ON_SURFACE
                ),
            ),
            files_section,
        ]
        try:
            page.update()
        except Exception:
            pass

    async def _fetch_status():
        progress_bar.visible = True
        try:
            page.update()
        except Exception:
            pass

        code = (
            "import sys, os, json\n"
            "info = {}\n"
            "info['python'] = sys.version.split()[0]\n"
            "info['cwd'] = os.getcwd()\n"
            "try:\n"
            "    info['files'] = os.listdir('/content')\n"
            "except Exception:\n"
            "    info['files'] = []\n"
            "try:\n"
            "    import torch\n"
            "    info['torch'] = torch.__version__\n"
            "    info['cuda'] = torch.cuda.is_available()\n"
            "except Exception:\n"
            "    info['torch'] = None\n"
            "    info['cuda'] = False\n"
            "try:\n"
            "    import tensorflow as tf\n"
            "    info['tf'] = tf.__version__\n"
            "except Exception:\n"
            "    info['tf'] = None\n"
            "print('__JSON_STATUS__:' + json.dumps(info))\n"
        )
        try:
            outputs = await colab.exec_code(code, session_name, timeout=12.0)
            json_data = None
            raw_text = []
            for o in outputs:
                if o.get("output_type") == "stream":
                    txt = o.get("text", "")
                    raw_text.append(txt)
                    if "__JSON_STATUS__:" in txt:
                        parts = txt.split("__JSON_STATUS__:")
                        if len(parts) > 1:
                            try:
                                json_data = json.loads(parts[1].strip().split("\n")[0])
                            except Exception:
                                pass
                elif o.get("output_type") == "error":
                    raw_text.append(f"Error: {o.get('ename')}: {o.get('evalue')}")

            if json_data:
                _render_gui_status(json_data)
            else:
                progress_bar.visible = False
                fallback_str = "".join(raw_text) or "No response from Colab VM."
                details_column.controls = [
                    ft.Text(
                        fallback_str,
                        size=tokens.FONT_SM,
                        color=ft.Colors.ON_SURFACE,
                    )
                ]
                page.update()
        except Exception as ex:
            progress_bar.visible = False
            details_column.controls = [
                ft.Row(
                    controls=[
                        ft.Icon(
                            ft.Icons.ERROR_OUTLINE_ROUNDED,
                            color=theme.ERROR,
                            size=tokens.ICON_MD,
                        ),
                        ft.Text(
                            f"Diagnostic failed: {ex}",
                            size=tokens.FONT_SM,
                            color=theme.ERROR,
                        ),
                    ],
                    spacing=tokens.SPACE_SM_XS,
                )
            ]
            try:
                page.update()
            except Exception:
                pass

    dlg = ft.AlertDialog(
        title=ft.Row(
            controls=[
                ft.Icon(
                    ft.Icons.CLOUD_DONE_ROUNDED,
                    size=tokens.ICON_BASE,
                    color=theme.SUCCESS,
                ),
                ft.Text(
                    "Colab VM Status",
                    weight=ft.FontWeight.W_600,
                    size=tokens.FONT_MD,
                ),
                ft.Container(expand=True),
                ft.Container(
                    content=ft.Text(
                        f"{session_name} ({state.session_hardware})",
                        size=tokens.FONT_XXS,
                        font_family="monospace",
                        weight=ft.FontWeight.BOLD,
                        color=theme.PRIMARY,
                    ),
                    padding=ft.Padding(
                        tokens.SPACE_SM_XS,
                        tokens.SPACE_XXS,
                        tokens.SPACE_SM_XS,
                        tokens.SPACE_XXS,
                    ),
                    border_radius=tokens.RADIUS_XS,
                    bgcolor=ft.Colors.with_opacity(
                        tokens.OPACITY_CONTAINER, theme.PRIMARY
                    ),
                ),
            ],
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=tokens.SPACE_SM,
        ),
        content=ft.Container(
            content=ft.Column(
                controls=[
                    progress_bar,
                    details_column,
                ],
                spacing=tokens.SPACE_SM,
                tight=True,
            ),
            width=tokens.DIALOG_WIDTH_SM,
        ),
        actions=[
            ft.TextButton(
                "Refresh",
                icon=ft.Icons.REFRESH_ROUNDED,
                on_click=lambda e: page.run_task(_fetch_status),
            ),
            ft.TextButton("Close", on_click=lambda e: page.pop_dialog()),
        ],
        actions_alignment=ft.MainAxisAlignment.END,
    )

    page.show_dialog(dlg)
    page.run_task(_fetch_status)
