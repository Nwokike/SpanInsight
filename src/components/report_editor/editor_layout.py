"""Full report editor layout assembly with header, reorderable block cards, AI edit section, and action buttons."""

from __future__ import annotations

import flet as ft

from components.report_editor.block_card import build_report_block_card
from core import theme, tokens


def build_report_editor(
    blocks: list[dict],
    title: str,
    description: str,
    on_blocks_changed,
    on_title_changed,
    on_desc_changed,
    on_save,
    on_share,
    on_view_live,
    on_back,
    on_import,
    on_ai_edit,
    on_voice_toggle,
    is_saving: bool = False,
    is_sharing: bool = False,
    is_viewing_live: bool = False,
    is_deleting: bool = False,
    is_recording: bool = False,
    is_transcribing: bool = False,
    is_ai_editing: bool = False,
    is_public: bool = False,
    on_public_changed=None,
    recording_time: int = 0,
    ai_prompt_text: str = "",
    recording_timer_ref: ft.Ref[ft.Text] | None = None,
    save_btn_ref: ft.Ref[ft.Control] | None = None,
    share_btn_ref: ft.Ref[ft.Control] | None = None,
    view_live_btn_ref: ft.Ref[ft.Control] | None = None,
    on_delete=None,
) -> list[ft.Control]:
    """Build the full report editor UI. Returns list of controls."""
    controls = []

    # Header
    controls.append(
        ft.Container(
            content=ft.Column(
                [
                    ft.Text(
                        "Edit Report",
                        weight="bold",
                        size=tokens.FONT_HEADING,
                    ),
                    ft.TextField(
                        value=title,
                        label="Report Title",
                        border_radius=tokens.RADIUS_MD_SM,
                        on_change=lambda e: on_title_changed(e.control.value),
                    ),
                    ft.TextField(
                        value=description,
                        label="Description",
                        border_radius=tokens.RADIUS_MD_SM,
                        max_lines=3,
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

    # Block cards
    total = len(blocks)

    def _move(idx, direction):
        j = idx + direction
        if 0 <= j < total:
            blocks[idx], blocks[j] = blocks[j], blocks[idx]
            on_blocks_changed()

    def _delete(idx):
        if 0 <= idx < len(blocks):
            blocks.pop(idx)
            on_blocks_changed()

    for i, block in enumerate(blocks):
        controls.append(
            ft.Container(
                content=build_report_block_card(
                    block, i, total, on_blocks_changed, _move, _delete
                ),
                margin=ft.Margin(
                    tokens.SPACE_XL,
                    tokens.SPACE_XS,
                    tokens.SPACE_XL,
                    tokens.SPACE_XS,
                ),
            )
        )

    # Import from Analysis button
    controls.append(
        ft.Container(
            content=ft.OutlinedButton(
                "Import Block from Analysis",
                icon=ft.Icons.ADD_CHART_ROUNDED,
                on_click=lambda e: on_import(),
                style=ft.ButtonStyle(
                    shape=ft.RoundedRectangleBorder(radius=tokens.RADIUS_MD_SM)
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

    # AI edit section
    ai_field_ref = ft.Ref[ft.TextField]()
    controls.append(
        ft.Container(
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
                                hint_text="e.g. 'Make descriptions more academic', 'Reorder by importance'...",
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
                    ft.ProgressBar(visible=is_ai_editing or is_transcribing),
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
                                else "AI is editing your report...",
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
                    # Row 1 - Primary actions
                    ft.Row(
                        [
                            ft.FilledButton(
                                ref=view_live_btn_ref,
                                content=ft.Row(
                                    [
                                        ft.ProgressRing(
                                            width=tokens.PROGRESS_RING_XS,
                                            height=tokens.PROGRESS_RING_XS,
                                            stroke_width=tokens.PROGRESS_RING_STROKE_THIN,
                                            color=ft.Colors.WHITE,
                                        ),
                                        ft.Text(
                                            "Opening...",
                                            size=tokens.FONT_BODY_SM,
                                        ),
                                    ],
                                    spacing=tokens.SPACE_SM_XS,
                                )
                                if is_viewing_live
                                else "View Live Report",
                                icon=ft.Icons.OPEN_IN_NEW_ROUNDED
                                if not is_viewing_live
                                else None,
                                style=ft.ButtonStyle(
                                    bgcolor=theme.PRIMARY,
                                    color=ft.Colors.WHITE,
                                    shape=ft.RoundedRectangleBorder(
                                        radius=tokens.RADIUS_MD
                                    ),
                                    padding=tokens.BUTTON_PADDING_MD,
                                ),
                                on_click=lambda e: on_view_live(),
                                disabled=is_viewing_live or is_ai_editing,
                                expand=True,
                            ),
                        ],
                        spacing=tokens.SPACE_SM,
                    ),
                    # Row 2 - Secondary actions
                    ft.Row(
                        [
                            ft.OutlinedButton(
                                content=ft.Row(
                                    [
                                        ft.ProgressRing(
                                            width=tokens.PROGRESS_RING_XS,
                                            height=tokens.PROGRESS_RING_XS,
                                            stroke_width=tokens.PROGRESS_RING_STROKE_THIN,
                                        ),
                                        ft.Text(
                                            "Back...",
                                            size=tokens.FONT_BODY_SM,
                                        ),
                                    ],
                                    spacing=tokens.SPACE_SM_XS,
                                )
                                if is_deleting
                                else "Back",
                                icon=ft.Icons.ARROW_BACK_ROUNDED
                                if not is_deleting
                                else None,
                                style=ft.ButtonStyle(
                                    shape=ft.RoundedRectangleBorder(
                                        radius=tokens.RADIUS_MD
                                    ),
                                    padding=tokens.BUTTON_PADDING_MD,
                                ),
                                on_click=lambda e: on_back(),
                                disabled=is_deleting,
                            ),
                            ft.FilledButton(
                                ref=save_btn_ref,
                                content=ft.Row(
                                    [
                                        ft.ProgressRing(
                                            width=tokens.PROGRESS_RING_XS,
                                            height=tokens.PROGRESS_RING_XS,
                                            stroke_width=tokens.PROGRESS_RING_STROKE_THIN,
                                            color=ft.Colors.WHITE,
                                        ),
                                        ft.Text(
                                            "Saving...",
                                            size=tokens.FONT_BODY_SM,
                                        ),
                                    ],
                                    spacing=tokens.SPACE_SM_XS,
                                )
                                if is_saving
                                else "Save",
                                icon=ft.Icons.SAVE_ROUNDED if not is_saving else None,
                                style=ft.ButtonStyle(
                                    bgcolor=theme.PRIMARY,
                                    color=ft.Colors.WHITE,
                                    shape=ft.RoundedRectangleBorder(
                                        radius=tokens.RADIUS_MD
                                    ),
                                    padding=tokens.BUTTON_PADDING_MD,
                                ),
                                on_click=lambda e: on_save(),
                                disabled=is_saving or is_ai_editing,
                            ),
                            ft.Container(
                                content=ft.Row(
                                    [
                                        ft.Icon(
                                            ft.Icons.PUBLIC_ROUNDED,
                                            size=tokens.ICON_SM,
                                            color=theme.PRIMARY
                                            if is_public
                                            else ft.Colors.ON_SURFACE_VARIANT,
                                        ),
                                        ft.Text(
                                            "Feature on spaninsight.com",
                                            size=tokens.FONT_BODY_SM,
                                            expand=True,
                                            color=theme.PRIMARY
                                            if is_public
                                            else ft.Colors.ON_SURFACE_VARIANT,
                                        ),
                                        ft.Switch(
                                            value=is_public,
                                            on_change=lambda e: (
                                                on_public_changed(e.control.value)
                                                if on_public_changed
                                                else None
                                            ),
                                        ),
                                    ],
                                    spacing=tokens.SPACE_SM,
                                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                                ),
                                padding=ft.Padding(
                                    tokens.SPACE_MD,
                                    tokens.SPACE_SM,
                                    tokens.SPACE_MD,
                                    tokens.SPACE_SM,
                                ),
                                border_radius=tokens.RADIUS_SM,
                                bgcolor=ft.Colors.with_opacity(
                                    tokens.OPACITY_FAINT, theme.PRIMARY
                                )
                                if is_public
                                else None,
                            ),
                            ft.OutlinedButton(
                                ref=share_btn_ref,
                                content=ft.Row(
                                    [
                                        ft.ProgressRing(
                                            width=tokens.PROGRESS_RING_XS,
                                            height=tokens.PROGRESS_RING_XS,
                                            stroke_width=tokens.PROGRESS_RING_STROKE_THIN,
                                        ),
                                        ft.Text(
                                            "Sharing...",
                                            size=tokens.FONT_BODY_SM,
                                        ),
                                    ],
                                    spacing=tokens.SPACE_SM_XS,
                                )
                                if is_sharing
                                else "Share",
                                icon=ft.Icons.SHARE_ROUNDED if not is_sharing else None,
                                style=ft.ButtonStyle(
                                    shape=ft.RoundedRectangleBorder(
                                        radius=tokens.RADIUS_MD
                                    ),
                                    padding=tokens.BUTTON_PADDING_MD,
                                    color=theme.PRIMARY,
                                ),
                                on_click=lambda e: on_share(),
                                disabled=is_sharing or is_ai_editing,
                            ),
                        ]
                        + (
                            [
                                ft.OutlinedButton(
                                    content=ft.Row(
                                        [
                                            ft.ProgressRing(
                                                width=tokens.PROGRESS_RING_XS,
                                                height=tokens.PROGRESS_RING_XS,
                                                stroke_width=tokens.PROGRESS_RING_STROKE_THIN,
                                                color=theme.ERROR,
                                            ),
                                            ft.Text(
                                                "Deleting...",
                                                size=tokens.FONT_BODY_SM,
                                                color=theme.ERROR,
                                            ),
                                        ],
                                        spacing=tokens.SPACE_SM_XS,
                                    )
                                    if is_deleting
                                    else "Delete Report",
                                    icon=ft.Icons.DELETE_FOREVER_ROUNDED
                                    if not is_deleting
                                    else None,
                                    icon_color=theme.ERROR,
                                    style=ft.ButtonStyle(
                                        color=theme.ERROR,
                                        shape=ft.RoundedRectangleBorder(
                                            radius=tokens.RADIUS_MD
                                        ),
                                        padding=tokens.BUTTON_PADDING_MD,
                                    ),
                                    on_click=lambda e: on_delete(),
                                    disabled=is_deleting or is_ai_editing,
                                )
                            ]
                            if on_delete is not None
                            else []
                        ),
                        spacing=tokens.SPACE_SM,
                        wrap=True,
                    ),
                ],
                spacing=tokens.SPACE_SM,
            ),
            padding=tokens.SPACE_XL,
            margin=ft.Margin(
                tokens.SPACE_XL,
                tokens.SPACE_SM,
                tokens.SPACE_XL,
                tokens.SPACE_SM,
            ),
            border_radius=tokens.RADIUS_LG,
            bgcolor=theme.GLASS_BG,
            border=ft.Border.all(tokens.DIVIDER_THICKNESS, theme.GLASS_BORDER_COLOR),
        )
    )

    controls.append(ft.Container(height=tokens.INPUT_WIDTH_SM))
    return controls
