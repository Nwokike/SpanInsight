"""Individual field card component for the form editor."""

from __future__ import annotations

import uuid

import flet as ft

from core import theme, tokens

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
    """Create a blank field dict with a unique label and a stable opaque id.

    ``name`` is the key collected responses are stored under, so it is a
    generated immutable id - NOT derived from the label. Renaming a question
    must never orphan its already-collected answers.
    """
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
        "name": "q_" + uuid.uuid4().hex[:10],
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
        # NOTE: ``name`` is intentionally NEVER regenerated here. It is the
        # storage key for collected responses; renaming a question must keep
        # its answers attached. Names are assigned once at creation.
        if schema is not None:
            new_s = [dict(f) for f in schema]
            if 0 <= index < len(new_s):
                new_s[index] = dict(field)
            on_change(new_s)
        else:
            on_change()

    def _update_options(val: str):
        field["options"] = [o.strip() for o in val.split(",") if o.strip()]
        if schema is not None:
            new_s = [dict(f) for f in schema]
            if 0 <= index < len(new_s):
                new_s[index] = dict(field)
            on_change(new_s)

    type_options = [ft.DropdownOption(key=t, text=t.upper()) for t in FIELD_TYPES]

    controls = [
        ft.Row(
            [
                ft.Icon(
                    TYPE_ICONS.get(field["type"], ft.Icons.TEXT_FIELDS),
                    size=tokens.ICON_SM,
                    color=theme.ACCENT,
                ),
                ft.TextField(
                    value=field["label"],
                    border=ft.InputBorder.NONE,
                    text_size=tokens.FONT_MD,
                    text_style=ft.TextStyle(weight=ft.FontWeight.W_500),
                    expand=True,
                    content_padding=ft.Padding(
                        tokens.SPACE_XS,
                        tokens.SPACE_NONE,
                        tokens.SPACE_XS,
                        tokens.SPACE_NONE,
                    ),
                    on_change=lambda e: _update("label", e.control.value),
                ),
                ft.Dropdown(
                    value=field["type"],
                    width=tokens.INPUT_WIDTH_MD,
                    text_size=tokens.FONT_SM,
                    options=type_options,
                    border_radius=tokens.RADIUS_SM,
                    content_padding=ft.Padding(
                        tokens.SPACE_SM,
                        tokens.SPACE_NONE,
                        tokens.SPACE_SM,
                        tokens.SPACE_NONE,
                    ),
                    on_select=lambda e: _update("type", e.data),
                ),
                ft.Switch(
                    value=field.get("required", False),
                    label="Req",
                    label_text_style=ft.TextStyle(size=tokens.FONT_XS),
                    on_change=lambda e: _update("required", e.control.value),
                ),
            ],
            spacing=tokens.SPACE_XS,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
    ]

    if field["type"] in HAS_OPTIONS:
        controls.append(
            ft.TextField(
                value=", ".join(field.get("options", [])),
                hint_text="Option 1, Option 2, Option 3...",
                text_size=tokens.FONT_BODY_SM,
                border_radius=tokens.RADIUS_SM,
                max_lines=2,
                on_change=lambda e: _update_options(e.control.value),
            )
        )

    controls.append(
        ft.Row(
            [
                ft.IconButton(
                    ft.Icons.ARROW_UPWARD_ROUNDED,
                    icon_size=tokens.ICON_SM,
                    disabled=index == 0,
                    on_click=lambda e, idx=index: on_move(idx, -1),
                ),
                ft.IconButton(
                    ft.Icons.ARROW_DOWNWARD_ROUNDED,
                    icon_size=tokens.ICON_SM,
                    disabled=index == total - 1,
                    on_click=lambda e, idx=index: on_move(idx, 1),
                ),
                ft.Container(expand=True),
                ft.IconButton(
                    ft.Icons.DELETE_OUTLINE_ROUNDED,
                    icon_size=tokens.ICON_SM,
                    icon_color=theme.ERROR,
                    on_click=lambda e, idx=index: on_delete(idx),
                ),
            ],
            spacing=tokens.SPACE_NONE,
        )
    )

    return ft.Container(
        content=ft.Column(controls, spacing=tokens.SPACE_SM_XS),
        padding=tokens.SPACE_MD,
        border_radius=tokens.RADIUS_MD_SM,
        bgcolor=ft.Colors.with_opacity(tokens.OPACITY_SUBTLE, ft.Colors.ON_SURFACE),
        border=ft.Border.all(tokens.DIVIDER_THICKNESS, theme.GLASS_BORDER_COLOR),
    )
