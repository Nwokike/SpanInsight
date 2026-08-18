"""AI Prompt modification and action box for Form Editor."""

from __future__ import annotations

import flet as ft

from core import theme


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
) -> ft.Container:
    """Build the AI edit input box with voice recording and publish controls."""
    ai_field_ref = ft.Ref[ft.TextField]()

    return ft.Container(
        content=ft.Column(
            [
                ft.Text(
                    "Edit with AI",
                    weight="bold",
                    size=13,
                    color=theme.ACCENT,
                ),
                ft.Row(
                    [
                        ft.TextField(
                            ref=ai_field_ref,
                            value=ai_prompt_text,
                            hint_text="e.g. 'Add a rating field', 'Make it shorter', 'Add demographics'...",
                            border_radius=10,
                            max_lines=2,
                            expand=True,
                            text_size=13,
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
                                    size=11,
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
                            spacing=2,
                            vertical_alignment="center",
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
                    spacing=4,
                    vertical_alignment="center",
                ),
                ft.ProgressBar(
                    visible=is_ai_editing or is_transcribing,
                ),
                ft.Row(
                    [
                        ft.ProgressRing(width=16, height=16, stroke_width=2),
                        ft.Text(
                            "Transcribing your voice..."
                            if is_transcribing
                            else "AI is editing your form...",
                            size=12,
                            color=theme.ACCENT,
                        ),
                    ],
                    spacing=8,
                    alignment="center",
                    visible=is_transcribing or is_ai_editing,
                ),
                ft.Divider(height=1, color=theme.GLASS_BORDER_COLOR),
                ft.Row(
                    [
                        ft.FilledButton(
                            "Publish",
                            icon=ft.Icons.PUBLISH_ROUNDED,
                            style=ft.ButtonStyle(
                                bgcolor=theme.PRIMARY,
                                color=ft.Colors.WHITE,
                                shape=ft.RoundedRectangleBorder(radius=12),
                                padding=14,
                            ),
                            on_click=lambda e: on_publish(),
                            disabled=is_publishing or is_ai_editing,
                        ),
                        ft.OutlinedButton(
                            "Cancel",
                            icon=ft.Icons.CLOSE_ROUNDED,
                            style=ft.ButtonStyle(
                                shape=ft.RoundedRectangleBorder(radius=12),
                                padding=14,
                                color=theme.PRIMARY,
                            ),
                            on_click=lambda e: on_cancel(),
                        ),
                    ],
                    spacing=8,
                ),
                ft.ProgressBar(visible=is_publishing),
            ],
            spacing=8,
        ),
        padding=20,
        margin=ft.Margin(20, 8, 20, 8),
        border_radius=16,
        bgcolor=theme.GLASS_BG,
        border=ft.Border.all(1, theme.GLASS_BORDER_COLOR),
    )
