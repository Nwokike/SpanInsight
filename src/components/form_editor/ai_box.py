"""AI Prompt modification and action box for Form Editor."""

from __future__ import annotations

import flet as ft

from core import theme, tokens


def build_ai_edit_box(
    on_ai_edit,
    on_voice_toggle,
    on_publish,
    on_cancel,
    is_publishing: bool = False,
    is_recording: bool = False,
    is_transcribing: bool = False,
    is_ai_editing: bool = False,
    recording_time: int = 0,
    ai_prompt_text: str = "",
    recording_timer_ref: ft.Ref[ft.Text] | None = None,
    publish_label: str = "Publish",
) -> ft.Container:
    """Build the AI edit input box with voice recording and publish controls."""
    ai_field_ref = ft.Ref[ft.TextField]()

    return ft.Container(
        content=ft.Column(
            [
                ft.Text(
                    "Edit with AI",
                    weight="bold",
                    size=tokens.FONT_BODY,
                    color=theme.ACCENT,
                ),
                ft.Row(
                    [
                        ft.TextField(
                            ref=ai_field_ref,
                            value=ai_prompt_text,
                            hint_text="e.g. 'Add a rating field', 'Make it shorter', 'Add demographics'...",
                            border_radius=tokens.RADIUS_MD_SM,
                            max_lines=2,
                            expand=True,
                            text_size=tokens.FONT_BODY,
                            disabled=is_ai_editing or is_recording,
                            on_change=lambda e: on_ai_edit(
                                "__set_text__", e.control.value
                            ),
                        ),
                        ft.Row(
                            [
                                ft.Text(
                                    ref=recording_timer_ref,
                                    value=f"00:{recording_time:02d} / 01:00",
                                    size=tokens.FONT_SM,
                                    color=theme.ERROR,
                                    weight="bold",
                                    visible=is_recording,
                                ),
                                ft.IconButton(
                                    ft.Icons.STOP_ROUNDED
                                    if is_recording
                                    else ft.Icons.MIC_ROUNDED,
                                    icon_color=theme.ERROR
                                    if is_recording
                                    else theme.ACCENT,
                                    tooltip="Stop" if is_recording else "Voice",
                                    on_click=on_voice_toggle,
                                    disabled=is_ai_editing,
                                ),
                            ],
                            spacing=tokens.SPACE_XXS,
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                        ft.IconButton(
                            ft.Icons.AUTO_FIX_HIGH_ROUNDED,
                            icon_color=theme.ACCENT,
                            tooltip="Apply AI edit",
                            on_click=lambda e: on_ai_edit(
                                "__submit__",
                                ai_field_ref.current.value
                                if ai_field_ref.current
                                else "",
                            ),
                            disabled=is_ai_editing or is_recording,
                        ),
                    ],
                    spacing=tokens.SPACE_XS,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                ft.ProgressBar(
                    visible=is_ai_editing or is_transcribing,
                ),
                ft.Row(
                    [
                        ft.ProgressRing(
                            width=tokens.PROGRESS_RING_SM,
                            height=tokens.PROGRESS_RING_SM,
                            stroke_width=tokens.PROGRESS_RING_STROKE_THIN,
                        ),
                        ft.Text(
                            "Transcribing your voice..."
                            if is_transcribing
                            else "AI is editing your form...",
                            size=tokens.FONT_BODY_SM,
                            color=theme.ACCENT,
                        ),
                    ],
                    spacing=tokens.SPACE_SM,
                    alignment=ft.MainAxisAlignment.CENTER,
                    visible=is_transcribing or is_ai_editing,
                ),
                ft.Divider(
                    height=tokens.DIVIDER_THICKNESS,
                    color=theme.GLASS_BORDER_COLOR,
                ),
                ft.Row(
                    [
                        ft.FilledButton(
                            publish_label,
                            icon=ft.Icons.PUBLISH_ROUNDED,
                            style=ft.ButtonStyle(
                                bgcolor=theme.PRIMARY,
                                color=ft.Colors.WHITE,
                                shape=ft.RoundedRectangleBorder(
                                    radius=tokens.RADIUS_MD
                                ),
                                padding=tokens.BUTTON_PADDING_MD,
                            ),
                            on_click=lambda e: on_publish(),
                            disabled=is_publishing or is_ai_editing,
                        ),
                        ft.OutlinedButton(
                            "Cancel",
                            icon=ft.Icons.CLOSE_ROUNDED,
                            style=ft.ButtonStyle(
                                shape=ft.RoundedRectangleBorder(
                                    radius=tokens.RADIUS_MD
                                ),
                                padding=tokens.BUTTON_PADDING_MD,
                                color=theme.PRIMARY,
                            ),
                            on_click=lambda e: on_cancel(),
                        ),
                    ],
                    spacing=tokens.SPACE_SM,
                ),
                ft.ProgressBar(visible=is_publishing),
            ],
            spacing=tokens.SPACE_SM,
        ),
        padding=tokens.SPACE_XL,
        margin=ft.Margin(
            tokens.SPACE_XL, tokens.SPACE_SM, tokens.SPACE_XL, tokens.SPACE_SM
        ),
        border_radius=tokens.RADIUS_LG,
        bgcolor=theme.GLASS_BG,
        border=ft.Border.all(tokens.DIVIDER_THICKNESS, theme.GLASS_BORDER_COLOR),
    )
