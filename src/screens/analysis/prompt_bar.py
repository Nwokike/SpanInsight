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
    on_toggle_expert_mode=None,
    is_expert_mode: bool = False,
) -> ft.Container:
    """Bottom-docked or inline AI prompt input with file picker, voice, and send."""
    disabled = is_generating or autopilot_running
    has_text = bool(prompt_text.strip())

    left_controls = [
        ft.IconButton(
            icon=ft.Icons.ATTACH_FILE_ROUNDED,
            icon_size=tokens.ICON_MD,
            tooltip="Import Data File",
            on_click=on_upload,
            style=ft.ButtonStyle(padding=tokens.SPACE_SM_XS),
        ),
    ]

    if on_toggle_expert_mode:
        left_controls.append(
            ft.IconButton(
                icon=ft.Icons.CODE_ROUNDED,
                icon_color=theme.PRIMARY
                if is_expert_mode
                else ft.Colors.ON_SURFACE_VARIANT,
                icon_size=tokens.ICON_MD,
                tooltip="Toggle Expert Code Input"
                if not is_expert_mode
                else "Switch to Natural Prompt",
                on_click=on_toggle_expert_mode,
                style=ft.ButtonStyle(padding=tokens.SPACE_SM_XS),
            )
        )

    return ft.Container(
        content=ft.Row(
            controls=[
                *left_controls,
                ft.TextField(
                    ref=prompt_ref,
                    value=prompt_text,
                    hint_text="Ask anything about your data, or enter Python code…"
                    if is_expert_mode
                    else "Ask anything about your data…",
                    text_size=tokens.FONT_SM,
                    text_style=ft.TextStyle(
                        font_family="RobotoMono" if is_expert_mode else None
                    ),
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
                    multiline=is_expert_mode,
                    min_lines=1 if not is_expert_mode else 3,
                    max_lines=6 if is_expert_mode else 3,
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
                    style=ft.ButtonStyle(padding=tokens.SPACE_SM_XS),
                ),
                ft.Container(
                    content=ft.IconButton(
                        icon=ft.Icons.PLAY_ARROW_ROUNDED
                        if is_expert_mode
                        else ft.Icons.SEND_ROUNDED,
                        icon_size=tokens.ICON_MD,
                        icon_color=ft.Colors.WHITE,
                        tooltip="Run Code" if is_expert_mode else "Send",
                        on_click=lambda _: on_submit(prompt_text),
                        disabled=is_generating or not has_text,
                        style=ft.ButtonStyle(padding=tokens.SPACE_SM_XS),
                    ),
                    bgcolor=theme.PRIMARY
                    if has_text
                    else ft.Colors.with_opacity(tokens.OPACITY_DIM, theme.PRIMARY),
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
        bgcolor=ft.Colors.with_opacity(tokens.OPACITY_SUBTLE, ft.Colors.ON_SURFACE),
        border=ft.Border.all(
            tokens.DIVIDER_THICKNESS,
            ft.Colors.with_opacity(tokens.OPACITY_MUTED, ft.Colors.ON_SURFACE),
        ),
        margin=ft.Margin(
            tokens.SPACE_MD, tokens.SPACE_SM, tokens.SPACE_MD, tokens.SPACE_SM
        ),
    )


def build_gen_indicator(
    is_generating: bool,
    stage_text: str = "",
    duration: float = 0.0,
) -> ft.Control:
    """Live AI agent progress pill shown while reasoning, generating, and executing."""
    from components.agent_progress_pill import build_agent_progress_pill

    if not is_generating:
        return ft.Container(visible=False)

    pill = build_agent_progress_pill(
        is_active=is_generating,
        stage_text=stage_text or "Reasoning & analyzing data…",
        duration=duration,
    )
    if not pill:
        return ft.Container(visible=False)
    return ft.Container(
        content=pill,
        padding=ft.Padding(
            tokens.SPACE_MD, tokens.SPACE_XS, tokens.SPACE_MD, tokens.SPACE_NONE
        ),
    )
