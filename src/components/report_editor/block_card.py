"""Individual editable report block card component."""

from __future__ import annotations

import flet as ft

from components.report_editor.visualizers import build_serialized_result_visualizer
from core import theme, tokens


def build_report_block_card(
    block: dict,
    index: int,
    total: int,
    on_change,
    on_move,
    on_delete,
) -> ft.Container:
    """Render one editable report block card with prompt, chart, table, description, reorder arrows, and delete action."""

    def _update_prompt(val):
        block["prompt"] = val

    def _update_desc(val):
        block["description"] = val
        on_change()

    # Chart image
    chart_widget = ft.Container(height=0)
    if block.get("figure_png_b64"):
        chart_widget = ft.Container(
            content=ft.Image(
                src=f"data:image/png;base64,{block['figure_png_b64']}",
                fit="contain",
                expand=True,
            ),
            height=240,
            border_radius=tokens.RADIUS_MD,
            clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
        )

    # Serialized result table or metrics
    res_widget = ft.Container(height=0)
    ser_res = block.get("serialized_result")
    stdout_val = block.get("stdout")

    if ser_res:
        vis = build_serialized_result_visualizer(ser_res)
        if vis:
            res_widget = ft.Container(
                content=vis,
                padding=tokens.SPACE_SM,
                border_radius=tokens.RADIUS_MD,
                bgcolor=ft.Colors.with_opacity(0.01, ft.Colors.ON_SURFACE),
            )
    elif stdout_val and str(stdout_val).strip() and str(stdout_val).strip() != "None":
        res_widget = ft.Container(
            content=ft.Text(
                str(stdout_val).strip(),
                size=10,
                font_family="RobotoMono",
                color="#E0E0E0",
            ),
            padding=tokens.SPACE_MD,
            bgcolor="#0D0D1A",
            border_radius=tokens.RADIUS_MD,
        )

    controls = [
        # Header with number + prompt
        ft.Row(
            [
                ft.Container(
                    content=ft.Text(
                        str(index + 1),
                        size=tokens.FONT_SM,
                        weight=ft.FontWeight.W_700,
                        color=ft.Colors.WHITE,
                        text_align=ft.TextAlign.CENTER,
                    ),
                    width=28,
                    height=28,
                    border_radius=14,
                    bgcolor=theme.PRIMARY,
                    alignment=ft.Alignment.CENTER,
                ),
                ft.TextField(
                    value=block.get("prompt", ""),
                    border="none",
                    text_size=14,
                    text_style=ft.TextStyle(weight=ft.FontWeight.W_600),
                    expand=True,
                    content_padding=ft.Padding(4, 0, 4, 0),
                    max_lines=2,
                    on_change=lambda e: _update_prompt(e.control.value),
                ),
            ],
            spacing=tokens.SPACE_MD,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        # Chart
        chart_widget,
        # Serialized result / table / metrics
        res_widget,
        # Description
        ft.Container(
            content=ft.Row(
                [
                    ft.Icon(
                        ft.Icons.LIGHTBULB_OUTLINE_ROUNDED,
                        size=tokens.ICON_SM,
                        color=theme.ACCENT,
                    ),
                    ft.TextField(
                        value=block.get("description", ""),
                        multiline=True,
                        border=ft.InputBorder.NONE,
                        content_padding=0,
                        text_size=13,
                        expand=True,
                        on_change=lambda e: _update_desc(e.control.value),
                    ),
                ],
                spacing=tokens.SPACE_SM,
                vertical_alignment=ft.CrossAxisAlignment.START,
            ),
            padding=tokens.SPACE_MD,
            border_radius=tokens.RADIUS_MD,
            bgcolor=ft.Colors.with_opacity(0.04, theme.ACCENT),
        ),
        # Reorder arrows and delete action
        ft.Row(
            [
                ft.IconButton(
                    ft.Icons.ARROW_UPWARD_ROUNDED,
                    icon_size=16,
                    disabled=index == 0,
                    on_click=lambda e, idx=index: on_move(idx, -1),
                    tooltip="Move up",
                ),
                ft.IconButton(
                    ft.Icons.ARROW_DOWNWARD_ROUNDED,
                    icon_size=16,
                    disabled=index == total - 1,
                    on_click=lambda e, idx=index: on_move(idx, 1),
                    tooltip="Move down",
                ),
                ft.IconButton(
                    ft.Icons.DELETE_OUTLINE_ROUNDED,
                    icon_size=16,
                    icon_color=theme.ERROR,
                    on_click=lambda e, idx=index: on_delete(idx),
                    tooltip="Delete block",
                ),
                ft.Container(expand=True),
                ft.Text(
                    f"Block {index + 1} of {total}",
                    size=11,
                    color=ft.Colors.ON_SURFACE_VARIANT,
                ),
            ],
            spacing=0,
        ),
    ]

    return ft.Container(
        content=ft.Column(controls, spacing=8),
        padding=14,
        border_radius=12,
        bgcolor=ft.Colors.with_opacity(0.04, ft.Colors.ON_SURFACE),
        border=ft.Border.all(1, theme.GLASS_BORDER_COLOR),
    )
