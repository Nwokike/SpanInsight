"""Form schema editor — editable field list with add/remove/reorder."""

from __future__ import annotations

import flet as ft

from core import theme

from .ai_box import build_ai_edit_box
from .field_card import FIELD_TYPES, build_field_card, new_field


def build_form_editor(
    schema: list[dict],
    title: str,
    description: str,
    on_schema_changed,
    on_title_changed,
    on_desc_changed,
    on_publish,
    on_cancel,
    on_ai_edit,
    on_voice_toggle,
    is_publishing: bool = False,
    is_recording: bool = False,
    is_transcribing: bool = False,
    is_ai_editing: bool = False,
    recording_time: int = 0,
    ai_prompt_text: str = "",
    recording_timer_ref: ft.Ref[ft.Text] | None = None,
) -> list[ft.Control]:
    """Build the full form editor UI. Returns a list of controls."""
    controls = []

    # 1. Header Information Box
    controls.append(
        ft.Container(
            content=ft.Column(
                [
                    ft.Text("Preview & Edit", weight="bold", size=16),
                    ft.TextField(
                        value=title,
                        label="Form Title",
                        border_radius=10,
                        on_change=lambda e: on_title_changed(e.control.value),
                    ),
                    ft.TextField(
                        value=description,
                        label="Description",
                        border_radius=10,
                        max_lines=2,
                        on_change=lambda e: on_desc_changed(e.control.value),
                    ),
                ],
                spacing=8,
            ),
            padding=20,
            margin=ft.Margin(20, 10, 20, 4),
            border_radius=16,
            bgcolor=theme.GLASS_BG,
            border=ft.Border.all(1, theme.GLASS_BORDER_COLOR),
        )
    )

    # 2. Field Cards List
    total = len(schema)

    def _move(idx, direction):
        j = idx + direction
        if 0 <= j < total:
            schema[idx], schema[j] = schema[j], schema[idx]
            on_schema_changed()

    def _delete(idx):
        schema.pop(idx)
        on_schema_changed()

    for i, field in enumerate(schema):
        controls.append(
            ft.Container(
                content=build_field_card(
                    field, i, total, on_schema_changed, _move, _delete, schema
                ),
                margin=ft.Margin(20, 4, 20, 4),
            )
        )

    # 3. Add Field Button
    controls.append(
        ft.Container(
            content=ft.OutlinedButton(
                "Add Field",
                icon=ft.Icons.ADD_ROUNDED,
                on_click=lambda e: (
                    schema.append(new_field(schema)),
                    on_schema_changed(),
                ),
                style=ft.ButtonStyle(
                    shape=ft.RoundedRectangleBorder(radius=12),
                    padding=14,
                ),
            ),
            padding=ft.Padding(20, 4, 20, 4),
        )
    )

    # 4. AI Edit & Publish Action Box
    controls.append(
        build_ai_edit_box(
            on_ai_edit=on_ai_edit,
            on_voice_toggle=on_voice_toggle,
            on_publish=on_publish,
            on_cancel=on_cancel,
            is_publishing=is_publishing,
            is_recording=is_recording,
            is_transcribing=is_transcribing,
            is_ai_editing=is_ai_editing,
            recording_time=recording_time,
            ai_prompt_text=ai_prompt_text,
            recording_timer_ref=recording_timer_ref,
        )
    )

    controls.append(ft.Container(height=100))
    return controls


__all__ = ["FIELD_TYPES", "build_field_card", "build_form_editor", "new_field"]
