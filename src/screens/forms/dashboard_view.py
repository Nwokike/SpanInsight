"""Forms dashboard view with AI prompt bar, form cards, and sponsored ad."""

from __future__ import annotations

import flet as ft

from components.brand_header import build_brand_header
from components.refresh_button import build_refresh_button
from core import theme, utils
from screens.forms.form_card import render_form_card


def build_forms_dashboard(
    page: ft.Page,
    user_forms: list[dict],
    is_loading: bool,
    is_creating: bool,
    is_recording: bool,
    is_transcribing: bool,
    recording_time: int,
    prompt_text: str,
    set_prompt_text,
    on_create_form,
    on_voice_toggle,
    on_view_form,
    on_refresh,
) -> ft.Control:
    """Renders the main dashboard for surveys: AI prompt bar, form list, and status."""
    if is_loading:
        form_list_content = [
            ft.Container(
                content=ft.Row(
                    [
                        ft.ProgressRing(width=16, height=16),
                        ft.Text("Loading forms..."),
                    ],
                    spacing=10,
                    alignment="center",
                ),
                padding=20,
            )
        ]
    elif not user_forms:
        form_list_content = [
            ft.Container(
                content=ft.Column(
                    [
                        ft.Icon(
                            ft.Icons.DYNAMIC_FORM_ROUNDED,
                            size=48,
                            color=ft.Colors.with_opacity(0.2, ft.Colors.ON_SURFACE),
                        ),
                        ft.Text(
                            "No forms yet",
                            color=ft.Colors.ON_SURFACE_VARIANT,
                            size=13,
                        ),
                        ft.Text(
                            "Describe a survey topic above to generate your first form.",
                            size=11,
                            color=ft.Colors.ON_SURFACE_VARIANT,
                            text_align="center",
                        ),
                    ],
                    spacing=8,
                    horizontal_alignment="center",
                ),
                padding=40,
                alignment=ft.Alignment.CENTER,
            )
        ]
    else:
        form_list_content = [
            render_form_card(form, on_view_form) for form in user_forms
        ]

    is_mobile = (
        page.platform in (ft.PagePlatform.ANDROID, ft.PagePlatform.IOS)
        if page
        else False
    )

    def _build_ad_banner():
        if not is_mobile:
            return ft.Container()
        return ft.Container(
            content=ft.Column(
                [
                    ft.Text(
                        "SPONSORED",
                        size=8,
                        weight=ft.FontWeight.W_700,
                        color=ft.Colors.ON_SURFACE_VARIANT,
                        style=ft.TextStyle(letter_spacing=1),
                    ),
                    utils.get_banner_ad(),
                ],
                horizontal_alignment="center",
                spacing=4,
            ),
            alignment=ft.Alignment.CENTER,
            padding=8,
            border_radius=12,
            bgcolor=theme.GLASS_BG,
            border=ft.Border.all(1, theme.GLASS_BORDER_COLOR),
            margin=ft.Margin(20, 4, 20, 10),
        )

    return ft.Column(
        [
            build_brand_header(show_tagline=True, spacing_below=True),
            ft.Container(
                content=ft.Column(
                    [
                        ft.Text("Create a Survey", weight="bold", size=16),
                        ft.Text(
                            "Describe your questionnaire, we will generate it, and you can edit before publishing.",
                            size=12,
                            color=ft.Colors.ON_SURFACE_VARIANT,
                        ),
                        ft.Container(height=8),
                        ft.Row(
                            [
                                ft.TextField(
                                    value=prompt_text,
                                    hint_text="e.g. A questionnaire on employee satisfaction",
                                    expand=True,
                                    border_radius=12,
                                    max_lines=3,
                                    min_lines=1,
                                    on_change=lambda e: set_prompt_text(
                                        e.control.value
                                    ),
                                    on_submit=on_create_form,
                                    disabled=is_creating or is_recording,
                                ),
                                ft.Row(
                                    [
                                        ft.Text(
                                            value=f"00:{recording_time:02d} / 01:00",
                                            size=11,
                                            color=theme.ERROR,
                                            weight="bold",
                                            visible=is_recording,
                                        ),
                                        ft.IconButton(
                                            icon=ft.Icons.STOP_ROUNDED
                                            if is_recording
                                            else ft.Icons.MIC_ROUNDED,
                                            icon_color=theme.ERROR
                                            if is_recording
                                            else theme.ACCENT,
                                            tooltip="Stop" if is_recording else "Voice",
                                            on_click=on_voice_toggle,
                                            disabled=is_creating,
                                        ),
                                    ],
                                    spacing=2,
                                    vertical_alignment="center",
                                ),
                                ft.IconButton(
                                    icon=ft.Icons.SEND_ROUNDED,
                                    icon_color=theme.PRIMARY,
                                    on_click=on_create_form,
                                    disabled=is_creating or is_recording,
                                ),
                            ],
                            spacing=4,
                            vertical_alignment="center",
                        ),
                        ft.ProgressBar(visible=is_creating or is_transcribing),
                        ft.Row(
                            [
                                ft.ProgressRing(width=16, height=16, stroke_width=2),
                                ft.Text(
                                    "Transcribing your voice...",
                                    size=12,
                                    color=theme.ACCENT,
                                ),
                            ],
                            spacing=8,
                            alignment="center",
                            visible=is_transcribing,
                        ),
                    ],
                    spacing=4,
                ),
                padding=16,
                margin=ft.Margin(20, 0, 20, 10),
                border_radius=16,
                bgcolor=theme.GLASS_BG,
                border=ft.Border.all(1, theme.GLASS_BORDER_COLOR),
            ),
            _build_ad_banner(),
            ft.Container(
                content=ft.Row(
                    [
                        ft.Text("Your Forms", weight="bold", size=16),
                        build_refresh_button(on_click=on_refresh),
                    ],
                    alignment="spaceBetween",
                ),
                padding=ft.Padding(20, 16, 20, 4),
            ),
            ft.Column(controls=form_list_content),
            _build_ad_banner(),
            ft.Container(height=100),
        ]
    )
