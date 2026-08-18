"""Visual output renderers (DataFrames, Plotly/PNG charts, ANSI text) for InsightCard."""

from __future__ import annotations

import base64
import logging
import re

import flet as ft

from components.ansi_parser import parse_ansi_to_flet_text
from core import theme, tokens

logger = logging.getLogger("InsightCard.Outputs")


def try_parse_dataframe_text(text: str) -> ft.Control | None:
    """Attempts to parse standard Pandas DataFrame text output into a styled DataTable."""
    lines = [line.strip() for line in text.strip().split("\n") if line.strip()]
    if len(lines) < 2:
        return None

    header_line = lines[0]
    cols = re.split(r"\s{2,}", header_line)
    if len(cols) < 2:
        return None

    try:
        data_rows = []
        for line in lines[1:50]:  # Cap at 50 rows for performance
            parts = re.split(r"\s{2,}", line)
            if len(parts) == len(cols):
                cells = [
                    ft.DataCell(
                        ft.Text(
                            p,
                            size=tokens.FONT_XS,
                            font_family="RobotoMono"
                            if re.match(r"^-?\d+(\.\d+)?$", p)
                            else None,
                        )
                    )
                    for p in parts
                ]
                data_rows.append(ft.DataRow(cells=cells))

        if len(data_rows) >= 1:
            data_cols = [
                ft.DataColumn(
                    ft.Text(
                        c,
                        size=tokens.FONT_XS,
                        weight=ft.FontWeight.W_600,
                        color=theme.PRIMARY,
                    )
                )
                for c in cols
            ]
            table = ft.DataTable(
                columns=data_cols,
                rows=data_rows,
                heading_row_height=34,
                data_row_max_height=30,
                column_spacing=16,
                horizontal_lines=ft.BorderSide(
                    1, ft.Colors.with_opacity(0.08, ft.Colors.ON_SURFACE)
                ),
                border=ft.Border.all(
                    1, ft.Colors.with_opacity(0.12, ft.Colors.ON_SURFACE)
                ),
                border_radius=tokens.RADIUS_SM,
            )
            return ft.Container(
                content=ft.Row([table], scroll=ft.ScrollMode.AUTO),
                border_radius=tokens.RADIUS_SM,
            )
    except Exception:
        pass
    return None


def render_chart_output(figure_png: bytes | str | None) -> ft.Control | None:
    """Render PNG figure output inside a rounded card container."""
    if not figure_png:
        return None
    try:
        b64_str = (
            base64.b64encode(figure_png).decode("utf-8")
            if isinstance(figure_png, bytes)
            else figure_png
        )
        return ft.Container(
            content=ft.Image(
                src=b64_str,
                fit=ft.BoxFit.CONTAIN,
                border_radius=tokens.RADIUS_MD,
            ),
            alignment=ft.Alignment.CENTER,
            padding=ft.Padding(0, tokens.SPACE_XS, 0, tokens.SPACE_XS),
        )
    except Exception as ex:
        logger.error("Chart render error: %s", ex)
        return None


def render_raw_output_drawer(
    raw_output_full: str,
    show_raw: bool,
    block: dict,
    page: ft.Page | None = None,
    on_change=None,
) -> ft.Control | None:
    """Collapsible raw kernel output terminal drawer."""
    if not raw_output_full:
        return None

    def _toggle_raw_output(_):
        block["_show_raw"] = not show_raw
        if on_change:
            on_change()

    async def _copy_raw_output(_=None):
        if not page:
            return
        try:
            await page.set_clipboard_async(raw_output_full)
            from core.utils import show_snack

            show_snack(page, "📋 Raw output copied to clipboard!", duration=2000)
        except Exception as ex:
            logger.error("Copy raw output failed: %s", ex)

    raw_toggle_btn = ft.TextButton(
        "Hide Raw Output" if show_raw else "View Raw Output",
        icon=ft.Icons.KEYBOARD_ARROW_UP_ROUNDED
        if show_raw
        else ft.Icons.KEYBOARD_ARROW_DOWN_ROUNDED,
        style=ft.ButtonStyle(color=ft.Colors.ON_SURFACE_VARIANT),
        on_click=_toggle_raw_output,
    )

    drawer_controls = [
        ft.Row([raw_toggle_btn], alignment=ft.MainAxisAlignment.START)
    ]
    if show_raw:
        raw_lines = max(raw_output_full.count("\n") + 1, 1)
        raw_height = min(max(raw_lines * 18 + 20, 50), 320)
        raw_output_box = ft.Container(
            content=ft.Column(
                [
                    ft.Row(
                        [
                            ft.Text(
                                "RAW KERNEL OUTPUT",
                                size=8,
                                color=ft.Colors.with_opacity(
                                    0.4, ft.Colors.ON_SURFACE
                                ),
                                weight=ft.FontWeight.W_600,
                            ),
                            ft.IconButton(
                                ft.Icons.COPY_ALL_ROUNDED,
                                icon_size=12,
                                tooltip="Copy Raw Output",
                                style=ft.ButtonStyle(padding=2),
                                on_click=lambda e: page.run_task(
                                    _copy_raw_output, e
                                )
                                if page
                                else None,
                            ),
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    ),
                    ft.Container(
                        content=ft.ListView(
                            [
                                parse_ansi_to_flet_text(
                                    raw_output_full, default_size=tokens.FONT_XS
                                )
                            ],
                            scroll=ft.ScrollMode.AUTO,
                        ),
                        height=raw_height,
                    ),
                ],
                spacing=2,
            ),
            padding=tokens.SPACE_SM,
            bgcolor=theme.TERMINAL_BG,
            border_radius=tokens.RADIUS_SM,
        )
        drawer_controls.append(raw_output_box)

    return ft.Column(drawer_controls, spacing=tokens.SPACE_XXS)


def render_code_drawer(
    code: str,
    show_code: bool,
    block: dict,
    on_run_code=None,
    on_change=None,
) -> ft.Control | None:
    """Collapsible code terminal drawer with runnable editor."""
    if not code:
        return None

    def _toggle_code(_):
        block["_show_code"] = not show_code
        if on_change:
            on_change()

    code_toggle_btn = ft.TextButton(
        "Hide Code" if show_code else "View Code",
        icon=ft.Icons.KEYBOARD_ARROW_UP_ROUNDED
        if show_code
        else ft.Icons.KEYBOARD_ARROW_DOWN_ROUNDED,
        style=ft.ButtonStyle(color=ft.Colors.ON_SURFACE_VARIANT),
        on_click=_toggle_code,
    )

    code_drawer_controls = [
        ft.Row([code_toggle_btn], alignment=ft.MainAxisAlignment.START)
    ]
    if show_code:
        code_field_ref = ft.Ref[ft.TextField]()
        code_terminal = ft.Container(
            content=ft.Column(
                [
                    ft.Row(
                        [
                            ft.Row(
                                [
                                    ft.Container(
                                        width=10,
                                        height=10,
                                        border_radius=5,
                                        bgcolor="#FF5F56",
                                    ),
                                    ft.Container(
                                        width=10,
                                        height=10,
                                        border_radius=5,
                                        bgcolor="#FFBD2E",
                                    ),
                                    ft.Container(
                                        width=10,
                                        height=10,
                                        border_radius=5,
                                        bgcolor="#28C840",
                                    ),
                                    ft.Text(
                                        "analysis.py",
                                        size=11,
                                        color=ft.Colors.ON_SURFACE_VARIANT,
                                    ),
                                ],
                                spacing=tokens.SPACE_XS,
                            ),
                            ft.TextButton(
                                "Run",
                                icon=ft.Icons.PLAY_ARROW_ROUNDED,
                                style=ft.ButtonStyle(color=theme.SUCCESS),
                                on_click=lambda _: (
                                    on_run_code(
                                        code_field_ref.current.value
                                        if code_field_ref.current
                                        else code
                                    )
                                    if on_run_code
                                    else None
                                ),
                            ),
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    ),
                    ft.TextField(
                        ref=code_field_ref,
                        value=code,
                        multiline=True,
                        min_lines=2,
                        max_lines=15,
                        text_size=tokens.FONT_SM,
                        text_style=ft.TextStyle(
                            font_family="RobotoMono",
                            color=ft.Colors.ON_SURFACE,
                        ),
                        border=ft.InputBorder.NONE,
                        bgcolor=ft.Colors.TRANSPARENT,
                        cursor_color=theme.PRIMARY,
                    ),
                ],
                spacing=tokens.SPACE_XXS,
            ),
            padding=tokens.SPACE_SM,
            bgcolor=ft.Colors.with_opacity(0.06, ft.Colors.BLACK),
            border_radius=tokens.RADIUS_SM,
            border=ft.Border.all(
                1, ft.Colors.with_opacity(0.12, ft.Colors.ON_SURFACE)
            ),
        )
        code_drawer_controls.append(code_terminal)

    return ft.Column(code_drawer_controls, spacing=tokens.SPACE_XXS)
