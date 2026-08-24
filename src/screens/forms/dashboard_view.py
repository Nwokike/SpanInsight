"""Forms dashboard view with AI prompt bar, form cards, and sponsored ad."""

from __future__ import annotations

import flet as ft

from components.brand_header import build_brand_header
from components.refresh_button import build_refresh_button
from core import theme, tokens, utils
from screens.forms.form_card import render_form_card
from screens.forms.templates import TEMPLATES


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
                        ft.ProgressRing(
                            width=tokens.PROGRESS_RING_SM,
                            height=tokens.PROGRESS_RING_SM,
                        ),
                        ft.Text("Loading forms..."),
                    ],
                    spacing=tokens.SPACE_MD_SM,
                    alignment=ft.MainAxisAlignment.CENTER,
                ),
                padding=tokens.SPACE_XL,
            )
        ]
    elif not user_forms:
        form_list_content = [
            ft.Container(
                content=ft.Column(
                    [
                        ft.Icon(
                            ft.Icons.DYNAMIC_FORM_ROUNDED,
                            size=tokens.ICON_HERO,
                            color=ft.Colors.with_opacity(
                                tokens.OPACITY_BORDER, ft.Colors.ON_SURFACE
                            ),
                        ),
                        ft.Text(
                            "No forms yet",
                            color=ft.Colors.ON_SURFACE_VARIANT,
                            size=tokens.FONT_BODY,
                        ),
                        ft.Text(
                            "Describe a survey topic above to generate your first form.",
                            size=tokens.FONT_SM,
                            color=ft.Colors.ON_SURFACE_VARIANT,
                            text_align=ft.TextAlign.CENTER,
                        ),
                    ],
                    spacing=tokens.SPACE_SM,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                padding=tokens.ICON_CONTAINER_SIZE,
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
                        size=tokens.FONT_XXS,
                        weight=ft.FontWeight.W_700,
                        color=ft.Colors.ON_SURFACE_VARIANT,
                        style=ft.TextStyle(letter_spacing=1),
                    ),
                    utils.get_banner_ad(),
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=tokens.SPACE_XS,
            ),
            alignment=ft.Alignment.CENTER,
            padding=tokens.SPACE_SM,
            border_radius=tokens.RADIUS_MD,
            bgcolor=theme.GLASS_BG,
            border=ft.Border.all(tokens.DIVIDER_THICKNESS, theme.GLASS_BORDER_COLOR),
            margin=ft.Margin(
                tokens.SPACE_XL,
                tokens.SPACE_XS,
                tokens.SPACE_XL,
                tokens.SPACE_MD_SM,
            ),
        )

    return [
        build_brand_header(show_tagline=True, spacing_below=True),
        ft.Container(
            content=ft.Column(
                [
                    ft.Text(
                        "Create a Survey",
                        weight="bold",
                        size=tokens.FONT_HEADING,
                    ),
                    ft.Text(
                        "Describe your questionnaire, we will generate it, and you can edit before publishing.",
                        size=tokens.FONT_BODY_SM,
                        color=ft.Colors.ON_SURFACE_VARIANT,
                    ),
                    ft.Container(height=tokens.SPACE_SM),
                    # Starter templates: one tap fills the prompt (flywheel).
                    ft.Row(
                        [
                            ft.ActionChip(
                                label=ft.Text(t["title"], size=tokens.FONT_XS),
                                tooltip=t["prompt"][:120],
                                on_click=lambda e, _p=t["prompt"]: set_prompt_text(_p),
                            )
                            for t in TEMPLATES
                        ],
                        spacing=tokens.SPACE_XS,
                        wrap=True,
                    ),
                    ft.Row(
                        [
                            ft.TextField(
                                value=prompt_text,
                                hint_text="e.g. A questionnaire on employee satisfaction",
                                expand=True,
                                border_radius=tokens.RADIUS_MD,
                                max_lines=3,
                                min_lines=1,
                                on_change=lambda e: set_prompt_text(e.control.value),
                                on_submit=on_create_form,
                                disabled=is_creating or is_recording,
                            ),
                            ft.Row(
                                [
                                    ft.Text(
                                        value=f"00:{recording_time:02d} / 01:00",
                                        size=tokens.FONT_SM,
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
                                spacing=tokens.SPACE_XXS,
                                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                            ),
                            ft.IconButton(
                                icon=ft.Icons.SEND_ROUNDED,
                                icon_color=theme.PRIMARY,
                                on_click=on_create_form,
                                disabled=is_creating or is_recording,
                            ),
                        ],
                        spacing=tokens.SPACE_XS,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    ft.ProgressBar(visible=is_creating or is_transcribing),
                    ft.Row(
                        [
                            ft.ProgressRing(
                                width=tokens.PROGRESS_RING_SM,
                                height=tokens.PROGRESS_RING_SM,
                                stroke_width=tokens.PROGRESS_RING_STROKE_THIN,
                            ),
                            ft.Text(
                                "Transcribing your voice...",
                                size=tokens.FONT_BODY_SM,
                                color=theme.ACCENT,
                            ),
                        ],
                        spacing=tokens.SPACE_SM,
                        alignment=ft.MainAxisAlignment.CENTER,
                        visible=is_transcribing,
                    ),
                ],
                spacing=tokens.SPACE_XS,
            ),
            padding=tokens.SPACE_LG,
            margin=ft.Margin(
                tokens.SPACE_XL,
                tokens.SPACE_NONE,
                tokens.SPACE_XL,
                tokens.SPACE_MD_SM,
            ),
            border_radius=tokens.RADIUS_LG,
            bgcolor=theme.GLASS_BG,
            border=ft.Border.all(tokens.DIVIDER_THICKNESS, theme.GLASS_BORDER_COLOR),
        ),
        _build_ad_banner(),
        ft.Container(
            content=ft.Row(
                [
                    ft.Text(
                        "Your Forms",
                        weight="bold",
                        size=tokens.FONT_HEADING,
                    ),
                    build_refresh_button(on_click=on_refresh),
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            ),
            padding=ft.Padding(
                tokens.SPACE_XL,
                tokens.SPACE_LG,
                tokens.SPACE_XL,
                tokens.SPACE_XS,
            ),
        ),
        *form_list_content,
        _build_ad_banner(),
        ft.Container(height=tokens.INPUT_WIDTH_SM),
    ]
