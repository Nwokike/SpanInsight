"""Insight Card component — presents analytical takeaways, visualizations, and raw telemetry."""

from __future__ import annotations

import base64
import logging
import re

import flet as ft

from components.ansi_parser import parse_ansi_to_flet_text
from core import theme, tokens

logger = logging.getLogger("InsightCard")


def _try_parse_dataframe_text(text: str) -> ft.Control | None:
    """Attempts to parse standard Pandas DataFrame text output into a styled DataTable."""
    lines = [line.strip() for line in text.strip().split("\n") if line.strip()]
    if len(lines) < 2:
        return None

    # Check if lines have whitespace-separated tabular structure
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


def build_insight_card(
    block: dict,
    index: int = 0,
    page: ft.Page | None = None,
    on_run_code=None,
    on_retry_ai=None,
    on_delete=None,
    on_pin=None,
    on_change=None,
    on_suggestion_selected=None,
) -> ft.Control:
    """Builds a card representing an analytical unit with intelligence takeaways and outputs."""
    is_running = block.get("is_running", False)
    is_failed = block.get("failed", False)
    prompt = block.get("prompt", "Data Analysis")
    code = block.get("code") or block.get("source", "")
    show_code = block.get("_show_code", False)
    show_raw = block.get("_show_raw", False)
    is_pinned = block.get("pinned", False)

    controls = []

    # ── 1. Top Header Row ─────────────────────────────────────────
    pin_btn = ft.IconButton(
        icon=ft.Icons.PUSH_PIN_ROUNDED if is_pinned else ft.Icons.PUSH_PIN_OUTLINED,
        icon_color=theme.ACCENT if is_pinned else ft.Colors.ON_SURFACE_VARIANT,
        icon_size=16,
        tooltip="Unpin from Report" if is_pinned else "Pin to Report",
        on_click=lambda _: on_pin(block) if on_pin else None,
        style=ft.ButtonStyle(padding=2),
    )

    delete_btn = ft.IconButton(
        icon=ft.Icons.CLOSE_ROUNDED,
        icon_color=ft.Colors.ON_SURFACE_VARIANT,
        icon_size=16,
        tooltip="Remove Step",
        on_click=lambda _: on_delete() if on_delete else None,
        style=ft.ButtonStyle(padding=2),
    )

    header_row = ft.Row(
        controls=[
            ft.Row(
                [
                    ft.Icon(
                        ft.Icons.AUTO_AWESOME_ROUNDED
                        if not is_failed
                        else ft.Icons.ERROR_OUTLINE_ROUNDED,
                        size=16,
                        color=theme.PRIMARY if not is_failed else theme.ERROR,
                    ),
                    ft.Text(
                        prompt,
                        size=tokens.FONT_SM,
                        weight=ft.FontWeight.W_600,
                        color=ft.Colors.ON_SURFACE,
                    ),
                ],
                spacing=tokens.SPACE_XS,
                expand=True,
            ),
            ft.Row([pin_btn, delete_btn], spacing=0),
        ],
        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
    )
    controls.append(header_row)

    # ── 2. Running Spinner ────────────────────────────────────────
    if is_running:
        controls.append(
            ft.Container(
                content=ft.Row(
                    [
                        ft.ProgressRing(width=16, height=16, stroke_width=2),
                        ft.Text(
                            "Executing analysis code...",
                            size=tokens.FONT_XS,
                            color=ft.Colors.ON_SURFACE_VARIANT,
                        ),
                    ],
                    spacing=tokens.SPACE_SM,
                ),
                padding=tokens.SPACE_SM,
            )
        )
        return ft.Container(
            content=ft.Column(controls=controls, spacing=tokens.SPACE_SM),
            padding=tokens.SPACE_MD,
            border_radius=tokens.RADIUS_LG,
            bgcolor=theme.GLASS_BG,
            border=ft.Border.all(1, theme.GLASS_BORDER_COLOR),
            margin=ft.Margin(0, 0, 0, tokens.SPACE_SM),
        )

    # ── 3. Visual Execution Output (Charts & Data Tables) ────────
    outputs = block.get("outputs", [])
    figure_png = block.get("figure_png")
    raw_output_full = block.get("stdout", "").strip()

    # Extract base64 image and complete raw output text
    text_plain = ""
    for out in outputs:
        if isinstance(out, dict):
            otype = out.get("output_type") or out.get("type", "")
            if otype == "stream":
                txt = out.get("text", "")
                raw_output_full += ("\n" if raw_output_full else "") + str(txt)
            elif otype == "error":
                tb = "\n".join(out.get("traceback", []))
                raw_output_full += ("\n" if raw_output_full else "") + tb
            elif otype in ("execute_result", "display_data"):
                data = out.get("data", {})
                if "image/png" in data and not figure_png:
                    try:
                        figure_png = base64.b64decode(data["image/png"])
                    except Exception:
                        pass
                if "text/plain" in data:
                    tp = str(data["text/plain"])
                    text_plain += ("\n" if text_plain else "") + tp
                    raw_output_full += ("\n" if raw_output_full else "") + tp

    # Render Chart if available
    if figure_png:
        try:
            b64_str = (
                base64.b64encode(figure_png).decode("utf-8")
                if isinstance(figure_png, bytes)
                else figure_png
            )
            chart_container = ft.Container(
                content=ft.Image(
                    src_base64=b64_str,
                    fit=ft.BoxFit.CONTAIN,
                    border_radius=tokens.RADIUS_MD,
                ),
                alignment=ft.Alignment.CENTER,
                padding=ft.Padding(0, tokens.SPACE_XS, 0, tokens.SPACE_XS),
            )
            controls.append(chart_container)
        except Exception as ex:
            logger.error("Chart render error: %s", ex)

    # Render Structured Table or Rich Text Output
    result_val = block.get("result") or text_plain or raw_output_full
    if result_val and str(result_val).strip() and str(result_val).strip() != "None":
        val_str = str(result_val).strip()
        table_ctrl = _try_parse_dataframe_text(val_str)
        if table_ctrl:
            controls.append(table_ctrl)
        else:
            parsed_ctrl = parse_ansi_to_flet_text(val_str, default_size=tokens.FONT_SM)
            controls.append(
                ft.Container(
                    content=parsed_ctrl,
                    padding=tokens.SPACE_SM,
                    bgcolor=ft.Colors.with_opacity(0.04, ft.Colors.ON_SURFACE),
                    border_radius=tokens.RADIUS_SM,
                    border=ft.Border.all(
                        1, ft.Colors.with_opacity(0.08, ft.Colors.ON_SURFACE)
                    ),
                )
            )

    # ── 4. Collapsible Raw Output Drawer (Complete Telemetry) ────
    if raw_output_full:

        def _toggle_raw_output(_):
            block["_show_raw"] = not show_raw
            if on_change:
                on_change()

        async def _copy_raw_output(_=None):
            if not page:
                return
            try:
                if hasattr(page, "set_clipboard_async"):
                    await page.set_clipboard_async(raw_output_full)
                else:
                    await ft.Clipboard().set(raw_output_full)
                page.snack_bar = ft.SnackBar(
                    ft.Text("📋 Raw output copied to clipboard!"), duration=2000
                )
                page.snack_bar.open = True
                page.update()
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
                                    ),
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

        controls.append(
            ft.Column(
                drawer_controls,
                spacing=tokens.SPACE_XXS,
            )
        )

    # ── 5. AI Executive Narration (Lightbulb Insight Callout) ────
    narration = (
        block.get("narration")
        or block.get("description")
        or ("Analyzing dataset patterns..." if not is_failed else "")
    )
    if narration and not is_failed:
        controls.append(
            ft.Container(
                content=ft.Row(
                    [
                        ft.Icon(
                            ft.Icons.LIGHTBULB_ROUNDED,
                            size=18,
                            color=theme.ACCENT,
                        ),
                        ft.Text(
                            narration,
                            size=tokens.FONT_SM,
                            weight=ft.FontWeight.W_500,
                            color=ft.Colors.ON_SURFACE,
                            expand=True,
                        ),
                    ],
                    vertical_alignment=ft.CrossAxisAlignment.START,
                    spacing=tokens.SPACE_SM,
                ),
                padding=tokens.SPACE_MD,
                bgcolor=ft.Colors.with_opacity(0.08, theme.ACCENT),
                border_radius=tokens.RADIUS_MD,
                border=ft.Border.all(1, ft.Colors.with_opacity(0.2, theme.ACCENT)),
            )
        )

    # ── 6. Collapsible Code Drawer (State-driven) ───────────────
    if code:

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
                                    "▶ Run",
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

        controls.append(
            ft.Column(
                code_drawer_controls,
                spacing=tokens.SPACE_XXS,
            )
        )

    # ── 7. Failure / Retry Option ────────────────────────────────
    if is_failed and on_retry_ai:
        controls.append(
            ft.Row(
                [
                    ft.TextButton(
                        "Retry with AI Self-Healing",
                        icon=ft.Icons.REFRESH_ROUNDED,
                        style=ft.ButtonStyle(color=theme.WARNING),
                        on_click=lambda _: on_retry_ai(prompt),
                    )
                ],
                alignment=ft.MainAxisAlignment.END,
            )
        )

    # ── 8. Follow-up Contextual Suggestions ─────────────────────
    suggestions = block.get("suggestions", [])
    if suggestions and on_suggestion_selected:
        sugg_chips = []
        for s in suggestions[:3]:
            if isinstance(s, dict):
                label_txt = s.get("label") or s.get("prompt", "")
                icon_txt = s.get("icon", "✨")
                prompt_val = s.get("prompt") or label_txt
                disp = f"{icon_txt} {label_txt}".strip()
            else:
                prompt_val = str(s)
                disp = str(s)

            sugg_chips.append(
                ft.Chip(
                    label=ft.Text(disp, size=tokens.FONT_XS),
                    tooltip=prompt_val,
                    on_click=lambda _, p=prompt_val: on_suggestion_selected(p),
                )
            )

        controls.append(
            ft.Column(
                [
                    ft.Text(
                        "Suggested next steps:",
                        size=tokens.FONT_XS,
                        weight=ft.FontWeight.W_600,
                        color=ft.Colors.ON_SURFACE_VARIANT,
                    ),
                    ft.Row(sugg_chips, wrap=True, spacing=tokens.SPACE_XXS),
                ],
                spacing=tokens.SPACE_XXS,
            )
        )

    return ft.Container(
        content=ft.Column(controls=controls, spacing=tokens.SPACE_SM),
        padding=tokens.SPACE_MD,
        border_radius=tokens.RADIUS_LG,
        bgcolor=theme.GLASS_BG,
        border=ft.Border.all(1, theme.GLASS_BORDER_COLOR),
        margin=ft.Margin(0, 0, 0, tokens.SPACE_SM),
    )
