"""AI Prompt bar and generation status indicator components for Analysis screen."""

from __future__ import annotations

import flet as ft

from core import theme, tokens


def build_prompt_bar(
    prompt_ref: ft.Ref[ft.TextField],
    prompt_text: str,
    set_prompt_text,
    is_generating: bool,
    is_recording: bool,
    autopilot_running: bool,
    on_submit,
    on_upload,
    on_toggle_voice,
) -> ft.Container:
    """Bottom-docked or inline AI prompt input with file picker, voice, and send."""
    disabled = is_generating or autopilot_running
    has_text = bool(prompt_text.strip())

    return ft.Container(
        content=ft.Row(
            controls=[
                ft.IconButton(
                    icon=ft.Icons.ATTACH_FILE_ROUNDED,
                    icon_size=tokens.ICON_MD,
                    tooltip="Import Data File",
                    on_click=on_upload,
                    style=ft.ButtonStyle(padding=6),
                ),
                ft.TextField(
                    ref=prompt_ref,
                    value=prompt_text,
                    hint_text="Ask anything about your data…",
                    text_size=tokens.FONT_SM,
                    border_color=ft.Colors.TRANSPARENT,
                    bgcolor=ft.Colors.TRANSPARENT,
                    expand=True,
                    on_change=lambda e: set_prompt_text(e.control.value),
                    on_submit=lambda e: on_submit(e.control.value),
                    content_padding=ft.Padding(
                        tokens.SPACE_SM,
                        tokens.SPACE_XS,
                        tokens.SPACE_SM,
                        tokens.SPACE_XS,
                    ),
                    max_lines=3,
                    disabled=disabled,
                ),
                ft.IconButton(
                    icon=ft.Icons.MIC_ROUNDED
                    if not is_recording
                    else ft.Icons.STOP_ROUNDED,
                    icon_size=tokens.ICON_MD,
                    icon_color=theme.ERROR if is_recording else None,
                    tooltip="Voice" if not is_recording else "Stop",
                    on_click=on_toggle_voice,
                    style=ft.ButtonStyle(padding=6),
                ),
                ft.Container(
                    content=ft.IconButton(
                        icon=ft.Icons.SEND_ROUNDED,
                        icon_size=tokens.ICON_MD,
                        icon_color=ft.Colors.WHITE,
                        tooltip="Send",
                        on_click=lambda _: on_submit(prompt_text),
                        disabled=is_generating or not has_text,
                        style=ft.ButtonStyle(padding=6),
                    ),
                    bgcolor=theme.PRIMARY
                    if has_text
                    else ft.Colors.with_opacity(0.3, theme.PRIMARY),
                    border_radius=tokens.RADIUS_MD,
                ),
            ],
            spacing=tokens.SPACE_XXS,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        padding=ft.Padding(
            tokens.SPACE_XS, tokens.SPACE_XS, tokens.SPACE_XS, tokens.SPACE_XS
        ),
        border_radius=tokens.RADIUS_LG,
        bgcolor=ft.Colors.with_opacity(0.04, ft.Colors.ON_SURFACE),
        border=ft.Border.all(1, ft.Colors.with_opacity(0.08, ft.Colors.ON_SURFACE)),
        margin=ft.Margin(tokens.SPACE_MD, tokens.SPACE_SM, tokens.SPACE_MD, 0),
    )


def build_gen_indicator(is_generating: bool) -> ft.Container:
    """Subtle spinner and caption shown while AI generates Python code."""
    if not is_generating:
        return ft.Container(visible=False)

    return ft.Container(
        content=ft.Row(
            controls=[
                ft.ProgressRing(width=14, height=14, stroke_width=2),
                ft.Text(
                    "AI is writing code…",
                    size=tokens.FONT_XS,
                    weight=ft.FontWeight.W_500,
                    italic=True,
                    color=ft.Colors.ON_SURFACE_VARIANT,
                ),
            ],
            spacing=tokens.SPACE_SM,
        ),
        padding=ft.Padding(
            tokens.SPACE_LG,
            tokens.SPACE_XS,
            tokens.SPACE_LG,
            tokens.SPACE_XS,
        ),
    )
