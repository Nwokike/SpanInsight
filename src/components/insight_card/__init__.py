"""Insight Card component - presents analytical takeaways, visualizations, and raw telemetry."""

from __future__ import annotations

import base64
import logging

import flet as ft

from components.ansi_parser import parse_ansi_to_flet_text
from components.thought_accordion import build_thought_accordion
from core import theme, tokens

from .actions import (
    build_card_header,
    build_executive_narration,
    build_retry_button,
    build_suggestion_chips,
)
from .outputs import (
    render_chart_output,
    render_code_drawer,
    render_raw_output_drawer,
    try_parse_dataframe_text,
)
from .skeleton import build_running_skeleton

logger = logging.getLogger("InsightCard")


def build_insight_card(
    block: dict,
    index: int = 0,
    page: ft.Page | None = None,
    on_run_code=None,
    on_retry_ai=None,
    on_delete=None,
    on_pin=None,
    on_pin_report=None,
    on_change=None,
    on_suggestion_selected=None,
    **kwargs,
) -> ft.Control:
    """Builds a card representing an analytical unit with intelligence takeaways and outputs."""
    is_running = block.get("is_running", False)
    is_failed = block.get("failed", False)
    prompt = block.get("prompt", "Data Analysis")
    code = block.get("code") or block.get("source", "")
    show_code = block.get("_show_code", False)
    show_raw = block.get("_show_raw", False)
    is_pinned = block.get("pinned", False)
    pin_fn = on_pin_report or on_pin

    controls = []

    # 1. Top Header Row
    controls.append(
        build_card_header(
            prompt=prompt,
            is_failed=is_failed,
            is_pinned=is_pinned,
            pin_fn=pin_fn,
            on_delete=on_delete,
            block=block,
        )
    )

    # 1.5. Collapsible AI Chain-of-Thought
    thought_ctrl = build_thought_accordion(block, on_change=on_change)
    if thought_ctrl:
        controls.append(thought_ctrl)

    # 2. Running Skeleton Placeholder
    if is_running:
        controls.append(build_running_skeleton())
        return ft.Container(
            content=ft.Column(controls=controls, spacing=tokens.SPACE_SM),
            padding=tokens.SPACE_MD,
            border_radius=tokens.RADIUS_LG,
            bgcolor=theme.GLASS_BG,
            border=ft.Border.all(1, theme.GLASS_BORDER_COLOR),
            margin=ft.Margin(0, 0, 0, tokens.SPACE_SM),
        )

    # 3. Visual Execution Output (Charts & Data Tables)
    outputs = block.get("outputs", [])
    figure_png = block.get("figure_png")
    raw_output_full = block.get("stdout", "").strip()

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

    structured = block.get("structured_result")
    structured_vis = None
    if isinstance(structured, dict) and structured.get("type"):
        try:
            from components.report_editor.visualizers import (
                build_serialized_result_visualizer,
            )

            structured_vis = build_serialized_result_visualizer(structured)
        except Exception as ex:
            logger.warning("Structured result render failed: %s", ex)

    native_chart_rendered = bool(
        isinstance(structured, dict)
        and structured.get("type") == "chart"
        and structured_vis is not None
    )

    # Render Chart if available
    if figure_png and not native_chart_rendered:
        chart_ctrl = render_chart_output(figure_png)
        if chart_ctrl:
            controls.append(chart_ctrl)

    # Render Structured Table or Rich Text Output
    if structured_vis is not None:
        controls.append(structured_vis)
    else:
        result_val = block.get("result") or text_plain or raw_output_full
        if result_val and str(result_val).strip() and str(result_val).strip() != "None":
            val_str = str(result_val).strip()
            table_ctrl = try_parse_dataframe_text(val_str)
            if table_ctrl:
                controls.append(table_ctrl)
            else:
                parsed_ctrl = parse_ansi_to_flet_text(
                    val_str, default_size=tokens.FONT_SM
                )
                controls.append(
                    ft.Container(
                        content=parsed_ctrl,
                        padding=tokens.SPACE_SM,
                        bgcolor=ft.Colors.with_opacity(
                            tokens.OPACITY_SUBTLE, ft.Colors.ON_SURFACE
                        ),
                        border_radius=tokens.RADIUS_SM,
                        border=ft.Border.all(
                            tokens.DIVIDER_THICKNESS,
                            ft.Colors.with_opacity(
                                tokens.OPACITY_MUTED, ft.Colors.ON_SURFACE
                            ),
                        ),
                    )
                )

    # 4. Collapsible Raw Output Drawer
    raw_drawer = render_raw_output_drawer(
        raw_output_full, show_raw, block, page=page, on_change=on_change
    )
    if raw_drawer:
        controls.append(raw_drawer)

    # 5. AI Executive Narration Callout
    narration = (
        block.get("narration")
        or block.get("description")
        or ("Analyzing dataset patterns..." if not is_failed else "")
    )
    narration_ctrl = build_executive_narration(narration, is_failed)
    if narration_ctrl:
        controls.append(narration_ctrl)

    # 6. Collapsible Code Drawer
    code_drawer = render_code_drawer(
        code, show_code, block, on_run_code=on_run_code, on_change=on_change
    )
    if code_drawer:
        controls.append(code_drawer)

    # 7. Failure / Retry Option
    retry_ctrl = build_retry_button(is_failed, prompt, on_retry_ai)
    if retry_ctrl:
        controls.append(retry_ctrl)

    # 8. Follow-up Contextual Suggestions
    sugg_ctrl = build_suggestion_chips(
        block.get("suggestions", []), on_suggestion_selected
    )
    if sugg_ctrl:
        controls.append(sugg_ctrl)

    return ft.Container(
        content=ft.Column(controls=controls, spacing=tokens.SPACE_SM),
        padding=tokens.SPACE_MD,
        border_radius=tokens.RADIUS_LG,
        bgcolor=theme.GLASS_BG,
        border=ft.Border.all(tokens.DIVIDER_THICKNESS, theme.GLASS_BORDER_COLOR),
        margin=ft.Margin(
            tokens.SPACE_NONE, tokens.SPACE_NONE, tokens.SPACE_NONE, tokens.SPACE_SM
        ),
    )


__all__ = ["build_insight_card"]
