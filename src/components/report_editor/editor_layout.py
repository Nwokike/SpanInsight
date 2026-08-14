"""Full report editor layout assembly with header, reorderable block cards, AI edit section, and action buttons."""

from __future__ import annotations

import flet as ft

from components.report_editor.block_card import build_report_block_card
from core import theme


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
                    ft.Text("Edit Report", weight="bold", size=16),
                    ft.TextField(
                        value=title,
                        label="Report Title",
                        border_radius=10,
                        on_change=lambda e: on_title_changed(e.control.value),
                    ),
                    ft.TextField(
                        value=description,
                        label="Description",
                        border_radius=10,
                        max_lines=3,
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
                margin=ft.Margin(20, 4, 20, 4),
            )
        )

    # Import from Analysis button
    controls.append(
        ft.Container(
            content=ft.OutlinedButton(
                "Import Block from Analysis",
                icon=ft.Icons.ADD_CHART_ROUNDED,
                on_click=lambda e: on_import(),
                style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10)),
            ),
            padding=ft.Padding(20, 4, 20, 4),
        )
    )

    # AI edit section
    ai_field_ref = ft.Ref[ft.TextField]()
    controls.append(
        ft.Container(
            content=ft.Column(
                [
                    ft.Text("Edit with AI", weight="bold", size=13, color=theme.ACCENT),
                    ft.Row(
                        [
                            ft.TextField(
                                ref=ai_field_ref,
                                value=ai_prompt_text,
                                hint_text="e.g. 'Make descriptions more academic', 'Reorder by importance'...",
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
                    ft.ProgressBar(visible=is_ai_editing or is_transcribing),
                    ft.Row(
                        [
                            ft.ProgressRing(width=16, height=16, stroke_width=2),
                            ft.Text(
                                "Transcribing your voice..."
                                if is_transcribing
                                else "AI is editing your report...",
                                size=12,
                                color=theme.ACCENT,
                            ),
                        ],
                        spacing=8,
                        alignment="center",
                        visible=is_transcribing or is_ai_editing,
                    ),
                    ft.Divider(height=1, color=theme.GLASS_BORDER_COLOR),
                    # Row 1 — Primary actions
                    ft.Row(
                        [
                            ft.FilledButton(
                                ref=view_live_btn_ref,
                                content=ft.Row(
                                    [
                                        ft.ProgressRing(
                                            width=12,
                                            height=12,
                                            stroke_width=2,
                                            color="white",
                                        ),
                                        ft.Text("Opening...", size=12),
                                    ],
                                    spacing=6,
                                )
                                if is_viewing_live
                                else "View Live Report",
                                icon=ft.Icons.OPEN_IN_NEW_ROUNDED
                                if not is_viewing_live
                                else None,
                                style=ft.ButtonStyle(
                                    bgcolor=theme.PRIMARY,
                                    color=ft.Colors.WHITE,
                                    shape=ft.RoundedRectangleBorder(radius=12),
                                    padding=14,
                                ),
                                on_click=lambda e: on_view_live(),
                                disabled=is_viewing_live or is_ai_editing,
                                expand=True,
                            ),
                        ],
                        spacing=8,
                    ),
                    # Row 2 — Secondary actions
                    ft.Row(
                        [
                            ft.OutlinedButton(
                                content=ft.Row(
                                    [
                                        ft.ProgressRing(
                                            width=12, height=12, stroke_width=2
                                        ),
                                        ft.Text("Back...", size=12),
                                    ],
                                    spacing=6,
                                )
                                if is_deleting
                                else "Back",
                                icon=ft.Icons.ARROW_BACK_ROUNDED
                                if not is_deleting
                                else None,
                                style=ft.ButtonStyle(
                                    shape=ft.RoundedRectangleBorder(radius=12),
                                    padding=14,
                                ),
                                on_click=lambda e: on_back(),
                                disabled=is_deleting,
                            ),
                            ft.FilledButton(
                                ref=save_btn_ref,
                                content=ft.Row(
                                    [
                                        ft.ProgressRing(
                                            width=12,
                                            height=12,
                                            stroke_width=2,
                                            color="white",
                                        ),
                                        ft.Text("Saving...", size=12),
                                    ],
                                    spacing=6,
                                )
                                if is_saving
                                else "Save",
                                icon=ft.Icons.SAVE_ROUNDED if not is_saving else None,
                                style=ft.ButtonStyle(
                                    bgcolor=theme.PRIMARY,
                                    color=ft.Colors.WHITE,
                                    shape=ft.RoundedRectangleBorder(radius=12),
                                    padding=14,
                                ),
                                on_click=lambda e: on_save(),
                                disabled=is_saving or is_ai_editing,
                            ),
                            ft.Container(
                                content=ft.Row(
                                    [
                                        ft.Icon(
                                            ft.Icons.PUBLIC_ROUNDED,
                                            size=16,
                                            color=theme.PRIMARY
                                            if is_public
                                            else ft.Colors.ON_SURFACE_VARIANT,
                                        ),
                                        ft.Text(
                                            "Feature on spaninsight.com",
                                            size=12,
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
                                    spacing=8,
                                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                                ),
                                padding=ft.Padding(12, 8, 12, 8),
                                border_radius=8,
                                bgcolor=ft.Colors.with_opacity(0.05, theme.PRIMARY)
                                if is_public
                                else None,
                            ),
                            ft.OutlinedButton(
                                ref=share_btn_ref,
                                content=ft.Row(
                                    [
                                        ft.ProgressRing(
                                            width=12, height=12, stroke_width=2
                                        ),
                                        ft.Text("Sharing...", size=12),
                                    ],
                                    spacing=6,
                                )
                                if is_sharing
                                else "Share",
                                icon=ft.Icons.SHARE_ROUNDED if not is_sharing else None,
                                style=ft.ButtonStyle(
                                    shape=ft.RoundedRectangleBorder(radius=12),
                                    padding=14,
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
                                                width=12,
                                                height=12,
                                                stroke_width=2,
                                                color=theme.ERROR,
                                            ),
                                            ft.Text(
                                                "Deleting...",
                                                size=12,
                                                color=theme.ERROR,
                                            ),
                                        ],
                                        spacing=6,
                                    )
                                    if is_deleting
                                    else "Delete Report",
                                    icon=ft.Icons.DELETE_FOREVER_ROUNDED
                                    if not is_deleting
                                    else None,
                                    icon_color=theme.ERROR,
                                    style=ft.ButtonStyle(
                                        color=theme.ERROR,
                                        shape=ft.RoundedRectangleBorder(radius=12),
                                        padding=14,
                                    ),
                                    on_click=lambda e: on_delete(),
                                    disabled=is_deleting or is_ai_editing,
                                )
                            ]
                            if on_delete is not None
                            else []
                        ),
                        spacing=8,
                        wrap=True,
                    ),
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
