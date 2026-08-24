"""Form schema editor - editable field list with add/remove/reorder."""

from __future__ import annotations

import flet as ft

from core import theme, tokens

from .ai_box import build_ai_edit_box
from .field_card import (
    FIELD_TYPES,
    HAS_OPTIONS,
    TYPE_ICONS,
    build_field_card,
    new_field,
)


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
    publish_label: str = "Publish",
) -> list[ft.Control]:
    """Build the full form editor UI. Returns a list of controls."""
    controls = []

    # 1. Header Information Box
    controls.append(
        ft.Container(
            content=ft.Column(
                [
                    ft.Text(
                        "Preview & Edit",
                        weight="bold",
                        size=tokens.FONT_HEADING,
                    ),
                    ft.TextField(
                        value=title,
                        label="Form Title",
                        border_radius=tokens.RADIUS_MD_SM,
                        on_change=lambda e: on_title_changed(e.control.value),
                    ),
                    ft.TextField(
                        value=description,
                        label="Description",
                        border_radius=tokens.RADIUS_MD_SM,
                        max_lines=2,
                        on_change=lambda e: on_desc_changed(e.control.value),
                    ),
                ],
                spacing=tokens.SPACE_SM,
            ),
            padding=tokens.SPACE_XL,
            margin=ft.Margin(
                tokens.SPACE_XL,
                tokens.SPACE_MD_SM,
                tokens.SPACE_XL,
                tokens.SPACE_XS,
            ),
            border_radius=tokens.RADIUS_LG,
            bgcolor=theme.GLASS_BG,
            border=ft.Border.all(tokens.DIVIDER_THICKNESS, theme.GLASS_BORDER_COLOR),
        )
    )

    # 2. Field Cards List
    total = len(schema)

    def _move(idx, direction):
        j = idx + direction
        if 0 <= j < total:
            new_s = [dict(f) for f in schema]
            new_s[idx], new_s[j] = new_s[j], new_s[idx]
            on_schema_changed(new_s)

    def _delete(idx):
        new_s = [dict(f) for i, f in enumerate(schema) if i != idx]
        on_schema_changed(new_s)

    for i, field in enumerate(schema):
        controls.append(
            ft.Container(
                content=build_field_card(
                    field, i, total, on_schema_changed, _move, _delete, schema
                ),
                margin=ft.Margin(
                    tokens.SPACE_XL,
                    tokens.SPACE_XS,
                    tokens.SPACE_XL,
                    tokens.SPACE_XS,
                ),
            )
        )

    # 3. Add Field Button
    controls.append(
        ft.Container(
            content=ft.OutlinedButton(
                "Add Field",
                icon=ft.Icons.ADD_ROUNDED,
                on_click=lambda e: on_schema_changed(
                    [*[dict(f) for f in schema], new_field(schema)]
                ),
                style=ft.ButtonStyle(
                    shape=ft.RoundedRectangleBorder(radius=tokens.RADIUS_MD),
                    padding=tokens.BUTTON_PADDING_MD,
                ),
            ),
            padding=ft.Padding(
                tokens.SPACE_XL,
                tokens.SPACE_XS,
                tokens.SPACE_XL,
                tokens.SPACE_XS,
            ),
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
            publish_label=publish_label,
        )
    )

    controls.append(ft.Container(height=tokens.INPUT_WIDTH_SM))
    return controls


__all__ = [
    "FIELD_TYPES",
    "HAS_OPTIONS",
    "TYPE_ICONS",
    "build_ai_edit_box",
    "build_field_card",
    "build_form_editor",
    "new_field",
]
