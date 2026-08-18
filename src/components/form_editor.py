"""Form schema editor — editable field list with add/remove/reorder."""

from __future__ import annotations

import flet as ft

from core import theme

FIELD_TYPES = [
    "text",
    "textarea",
    "number",
    "email",
    "select",
    "radio",
    "checkbox",
    "date",
    "phone",
    "url",
    "rating",
]

TYPE_ICONS = {
    "text": ft.Icons.SHORT_TEXT_ROUNDED,
    "textarea": ft.Icons.NOTES_ROUNDED,
    "number": ft.Icons.NUMBERS_ROUNDED,
    "email": ft.Icons.EMAIL_ROUNDED,
    "select": ft.Icons.LIST_ROUNDED,
    "radio": ft.Icons.RADIO_BUTTON_CHECKED_ROUNDED,
    "checkbox": ft.Icons.CHECK_BOX_ROUNDED,
    "date": ft.Icons.CALENDAR_TODAY_ROUNDED,
    "phone": ft.Icons.PHONE_ROUNDED,
    "url": ft.Icons.LINK_ROUNDED,
    "rating": ft.Icons.STAR_ROUNDED,
}

HAS_OPTIONS = {"select", "radio", "checkbox"}


def new_field(schema: list[dict], ftype="text") -> dict:
    """Create a blank field dict with a unique label."""
    existing_labels = {f["label"].lower() for f in schema}
    base_label = "New Field"
    if base_label.lower() not in existing_labels:
        label = base_label
    else:
        counter = 1
        while True:
            candidate = f"{base_label} {counter}"
            if candidate.lower() not in existing_labels:
                label = candidate
                break
            counter += 1

    return {
        "name": label.lower().replace(" ", "_"),
        "label": label,
        "type": ftype,
        "required": False,
        "options": [],
    }


def build_field_card(
    field: dict,
    index: int,
    total: int,
    on_change,
    on_move,
    on_delete,
    schema: list[dict] | None = None,
) -> ft.Container:
    """Render one editable field card."""

    def _update(key, val):
        field[key] = val
        if key == "label":
            base_name = val.lower().replace(" ", "_")
            name = base_name
            if schema:
                existing_names = {
                    schema[i]["name"] for i in range(len(schema)) if i != index
                }
                if name in existing_names:
                    counter = 1
                    while f"{base_name}_{counter}" in existing_names:
                        counter += 1
                    name = f"{base_name}_{counter}"
            field["name"] = name
        if key == "type":
            on_change()

    def _update_options(val: str):
        field["options"] = [o.strip() for o in val.split(",") if o.strip()]

    type_options = [ft.DropdownOption(key=t, text=t.upper()) for t in FIELD_TYPES]

    controls = [
        ft.Row(
            [
                ft.Icon(
                    TYPE_ICONS.get(field["type"], ft.Icons.TEXT_FIELDS),
                    size=16,
                    color=theme.ACCENT,
                ),
                ft.TextField(
                    value=field["label"],
                    border="none",
                    text_size=14,
                    text_style=ft.TextStyle(weight=ft.FontWeight.W_500),
                    expand=True,
                    content_padding=ft.Padding(4, 0, 4, 0),
                    on_change=lambda e: _update("label", e.control.value),
                ),
                ft.Dropdown(
                    value=field["type"],
                    width=110,
                    text_size=11,
                    options=type_options,
                    border_radius=8,
                    content_padding=ft.Padding(8, 0, 8, 0),
                    on_select=lambda e: _update("type", e.data),
                ),
                ft.Switch(
                    value=field.get("required", False),
                    label="Req",
                    label_text_style=ft.TextStyle(size=10),
                    on_change=lambda e: _update("required", e.control.value),
                ),
            ],
            spacing=4,
            vertical_alignment="center",
        ),
    ]

    if field["type"] in HAS_OPTIONS:
        controls.append(
            ft.TextField(
                value=", ".join(field.get("options", [])),
                hint_text="Option 1, Option 2, Option 3...",
                text_size=12,
                border_radius=8,
                max_lines=2,
                on_change=lambda e: _update_options(e.control.value),
            )
        )

    controls.append(
        ft.Row(
            [
                ft.IconButton(
                    ft.Icons.ARROW_UPWARD_ROUNDED,
                    icon_size=16,
                    disabled=index == 0,
                    on_click=lambda e, idx=index: on_move(idx, -1),
                ),
                ft.IconButton(
                    ft.Icons.ARROW_DOWNWARD_ROUNDED,
                    icon_size=16,
                    disabled=index == total - 1,
                    on_click=lambda e, idx=index: on_move(idx, 1),
                ),
                ft.Container(expand=True),
                ft.IconButton(
                    ft.Icons.DELETE_OUTLINE_ROUNDED,
                    icon_size=16,
                    icon_color=theme.ERROR,
                    on_click=lambda e, idx=index: on_delete(idx),
                ),
            ],
            spacing=0,
        )
    )

    return ft.Container(
        content=ft.Column(controls, spacing=6),
        padding=12,
        border_radius=10,
        bgcolor=ft.Colors.with_opacity(0.04, ft.Colors.ON_SURFACE),
        border=ft.Border.all(1, theme.GLASS_BORDER_COLOR),
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
) -> list[ft.Control]:
    """Build the full form editor UI. Returns a list of controls."""
    controls = []

    # Header
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

    # Field cards
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

    # Add field button
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

    # AI edit prompt with voice + animation (same pattern as create)
    ai_field_ref = ft.Ref[ft.TextField]()
    controls.append(
        ft.Container(
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
    )

    controls.append(ft.Container(height=100))
    return controls
