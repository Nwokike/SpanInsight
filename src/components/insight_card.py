"""InsightCard — SpanInsight's signature AI Data Intelligence Card.

Renders deterministic VM execution outputs (charts, data tables, metric cards),
AI executive narration, collapsible raw stdout output drawer, collapsible Python
code drawer, and interactive follow-up suggestion chips.
"""

from __future__ import annotations

import base64
import logging
from collections.abc import Callable

import flet as ft

from components.ansi_parser import parse_ansi_to_flet_text
from core import theme, tokens

logger = logging.getLogger("InsightCard")


def build_insight_card(
    block: dict,
    index: int,
    page: ft.Page,
    on_run_code: Callable[[str], None] | None = None,
    on_pin_report: Callable[[dict], None] | None = None,
    on_suggestion_selected: Callable[[str], None] | None = None,
    on_retry_ai: Callable[[str], None] | None = None,
    on_change: Callable[[], None] | None = None,
) -> ft.Container:
    """Build a comprehensive SpanInsight Insight Card with state-driven drawers."""
    prompt = block.get("prompt") or block.get("name") or f"Analysis #{index + 1}"
    code = block.get("code") or block.get("source") or ""
    is_failed = block.get("failed", False)
    is_pinned = block.get("pinned", False)
    is_running = block.get("is_running", False)
    show_raw = block.get("_show_raw", False)
    show_code = block.get("_show_code", False)

    controls: list[ft.Control] = []

    # ── 1. Card Header ──────────────────────────────────────────
    status_icon = ft.Icon(
        ft.Icons.ERROR_OUTLINE_ROUNDED if is_failed else ft.Icons.AUTO_AWESOME_ROUNDED,
        size=18,
        color=theme.ERROR if is_failed else theme.ACCENT,
    )
    title_text = ft.Text(
        prompt,
        size=tokens.FONT_MD,
        weight=ft.FontWeight.W_700,
        expand=True,
        max_lines=2,
        overflow=ft.TextOverflow.ELLIPSIS,
    )

    action_buttons = []

    # Copy action
    async def _on_copy(_):
        try:
            content_to_copy = code
            if block.get("stdout"):
                content_to_copy += f"\n\n# Output:\n{block.get('stdout')}"
            await ft.Clipboard().set(content_to_copy)
            if page:
                page.snack_bar = ft.SnackBar(
                    ft.Text("Code and outputs copied to clipboard!"),
                    duration=2000,
                )
                page.snack_bar.open = True
                page.update()
        except Exception as ex:
            logger.warning("Copy failed: %s", ex)

    copy_btn = ft.IconButton(
        icon=ft.Icons.CONTENT_COPY_ROUNDED,
        icon_size=16,
        tooltip="Copy Code & Output",
        on_click=lambda e: page.run_task(_on_copy, e),
    )
    action_buttons.append(copy_btn)

    # Pin to report action
    if on_pin_report and not is_failed:
        pin_btn = ft.IconButton(
            icon=ft.Icons.PUSH_PIN_ROUNDED if is_pinned else ft.Icons.PUSH_PIN_OUTLINED,
            icon_color=theme.ACCENT if is_pinned else ft.Colors.ON_SURFACE_VARIANT,
            icon_size=18,
            tooltip="Pinned to Report" if is_pinned else "Pin to Report",
            on_click=lambda _: on_pin_report(block),
        )
        action_buttons.append(pin_btn)

    header_row = ft.Row(
        [
            status_icon,
            title_text,
            ft.Row(action_buttons, spacing=tokens.SPACE_XXS),
        ],
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
    )
    controls.append(header_row)

    # ── 2. Loading State ────────────────────────────────────────
    if is_running:
        controls.append(
            ft.Container(
                content=ft.Row(
                    [
                        ft.ProgressRing(width=16, height=16, stroke_width=2),
                        ft.Text(
                            "Running analysis on Colab VM...",
                            size=tokens.FONT_SM,
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
    stdout_text = block.get("stdout", "").strip()

    # Extract base64 image if present in outputs
    if not figure_png:
        for out in outputs:
            data = out.get("data", {})
            if "image/png" in data:
                try:
                    figure_png = base64.b64decode(data["image/png"])
                    break
                except Exception:
                    pass

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

    # Extract text results & table output
    text_plain = ""
    for out in outputs:
        otype = out.get("output_type") or out.get("type", "")
        if otype == "stream":
            stdout_text += ("\n" if stdout_text else "") + out.get("text", "")
        elif otype in ("execute_result", "display_data"):
            data = out.get("data", {})
            if "text/plain" in data:
                text_plain += ("\n" if text_plain else "") + data["text/plain"]

    result_val = block.get("result") or text_plain
    if result_val and str(result_val).strip() and str(result_val).strip() != "None":
        parsed_ctrl = parse_ansi_to_flet_text(
            str(result_val).strip(), default_size=tokens.FONT_SM
        )
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

    # ── 4. Collapsible Raw Output Drawer (State-driven) ─────────
    if stdout_text and stdout_text != str(result_val).strip():

        def _toggle_raw_output(_):
            block["_show_raw"] = not show_raw
            if on_change:
                on_change()

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
            raw_output_box = ft.Container(
                content=parse_ansi_to_flet_text(
                    stdout_text, default_size=tokens.FONT_XS
                ),
                padding=tokens.SPACE_SM,
                bgcolor=ft.Colors.with_opacity(0.06, ft.Colors.BLACK),
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
                ft.ActionChip(
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
