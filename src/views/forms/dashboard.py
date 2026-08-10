from datetime import UTC

import flet as ft

from components.brand_header import build_brand_header
from components.refresh_button import build_refresh_button
from core import theme, utils

from .state import FormsState


def build_form_card(form: dict, on_view_form, page: ft.Page) -> ft.Container:
    is_expired = False
    try:
        from datetime import datetime

        exp = datetime.fromisoformat(form["expires_at"])
        is_expired = exp < datetime.now(UTC)
    except Exception:
        pass
    status_color = theme.ERROR if is_expired else theme.SUCCESS
    status_text = "Expired" if is_expired else "Active"
    return ft.Container(
        content=ft.Row(
            [
                ft.Column(
                    [
                        ft.Text(
                            form["title"],
                            weight="bold",
                            size=14,
                            max_lines=1,
                            overflow="ellipsis",
                        ),
                        ft.Row(
                            [
                                ft.Container(
                                    content=ft.Text(
                                        status_text,
                                        size=9,
                                        color=status_color,
                                        weight="bold",
                                    ),
                                    padding=ft.Padding(6, 2, 6, 2),
                                    border_radius=4,
                                    bgcolor=ft.Colors.with_opacity(0.1, status_color),
                                ),
                                ft.Text(
                                    f"{form.get('response_count', 0)} responses",
                                    size=11,
                                    color=ft.Colors.ON_SURFACE_VARIANT,
                                ),
                            ],
                            spacing=8,
                        ),
                    ],
                    spacing=4,
                    expand=True,
                ),
                ft.IconButton(
                    ft.Icons.ARROW_FORWARD_IOS_ROUNDED,
                    icon_size=16,
                    on_click=lambda e, f=form: page.run_task(on_view_form, f),
                ),
            ]
        ),
        padding=14,
        border_radius=12,
        bgcolor=theme.GLASS_BG,
        border=ft.Border.all(1, theme.GLASS_BORDER_COLOR),
        margin=ft.Margin(20, 0, 20, 8),
        on_click=lambda e, f=form: page.run_task(on_view_form, f),
        ink=True,
    )


def build_dashboard_layout(
    ui_state: FormsState, page: ft.Page, on_create_form, on_voice_toggle, load_forms
) -> ft.Column:
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
                                    ref=ui_state.form_prompt_field,
                                    value=ui_state.prompt_text["value"],
                                    hint_text="e.g. A questionnaire on employee satisfaction",
                                    expand=True,
                                    border_radius=12,
                                    max_lines=3,
                                    min_lines=1,
                                    on_change=lambda e: (
                                        ui_state.prompt_text.__setitem__(
                                            "value", e.control.value
                                        )
                                    ),
                                    on_submit=lambda e: page.run_task(
                                        on_create_form, e
                                    ),
                                    disabled=ui_state.is_creating["value"]
                                    or ui_state.is_recording["value"],
                                ),
                                ft.Row(
                                    [
                                        ft.Text(
                                            ref=ui_state.recording_timer,
                                            value=f"00:{ui_state.recording_time['value']:02d} / 01:00",
                                            size=11,
                                            color=theme.ERROR,
                                            weight="bold",
                                            visible=ui_state.is_recording["value"],
                                        ),
                                        ft.IconButton(
                                            ref=ui_state.dashboard_voice_button_ref,
                                            icon=ft.Icons.STOP_ROUNDED
                                            if ui_state.is_recording["value"]
                                            else ft.Icons.MIC_ROUNDED,
                                            icon_color=theme.ERROR
                                            if ui_state.is_recording["value"]
                                            else theme.ACCENT,
                                            tooltip="Stop"
                                            if ui_state.is_recording["value"]
                                            else "Voice",
                                            on_click=lambda e: page.run_task(
                                                on_voice_toggle, e
                                            ),
                                            disabled=ui_state.is_creating["value"],
                                        ),
                                    ],
                                    spacing=2,
                                    vertical_alignment="center",
                                ),
                                ft.IconButton(
                                    ref=ui_state.dashboard_send_button_ref,
                                    icon=ft.Icons.SEND_ROUNDED,
                                    icon_color=theme.PRIMARY,
                                    on_click=lambda e: page.run_task(on_create_form, e),
                                    disabled=ui_state.is_creating["value"]
                                    or ui_state.is_recording["value"],
                                ),
                            ],
                            spacing=4,
                            vertical_alignment="center",
                        ),
                        ft.ProgressBar(
                            ref=ui_state.dashboard_progress_bar_ref,
                            visible=ui_state.is_creating["value"]
                            or ui_state.is_transcribing["value"],
                        ),
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
                            visible=ui_state.is_transcribing["value"],
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
            # ── Banner Ad (Mobile Only) ──────────────────────────────────────
            ft.Container(
                content=ft.Column(
                    [
                        ft.Text(
                            "SPONSORED",
                            size=8,
                            weight=ft.FontWeight.W_700,
                            color=ft.Colors.ON_SURFACE_VARIANT,
                            style=ft.TextStyle(letter_spacing=1),
                        ),
                        utils.get_banner_ad(
                            unit_id="ca-app-pub-5679949845754640/5628404223",
                            width=320,
                            height=50,
                        ),
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
            if page.platform in (ft.PagePlatform.ANDROID, ft.PagePlatform.IOS)
            else ft.Container(),
            ft.Container(
                content=ft.Row(
                    [
                        ft.Text("Your Forms", weight="bold", size=16),
                        build_refresh_button(
                            on_click=lambda e: page.run_task(load_forms),
                        ),
                    ],
                    alignment="spaceBetween",
                ),
                padding=ft.Padding(20, 16, 20, 4),
            ),
            ft.Column(ref=ui_state.user_forms_column_ref, controls=[]),
            # ── Banner Ad After Forms (Mobile Only) ──────────────────────────
            ft.Container(
                content=ft.Column(
                    [
                        ft.Text(
                            "SPONSORED",
                            size=8,
                            weight=ft.FontWeight.W_700,
                            color=ft.Colors.ON_SURFACE_VARIANT,
                            style=ft.TextStyle(letter_spacing=1),
                        ),
                        utils.get_banner_ad(
                            unit_id="ca-app-pub-5679949845754640/5628404223",
                            width=320,
                            height=50,
                        ),
                    ],
                    horizontal_alignment="center",
                    spacing=4,
                ),
                alignment=ft.Alignment.CENTER,
                padding=8,
                border_radius=12,
                bgcolor=theme.GLASS_BG,
                border=ft.Border.all(1, theme.GLASS_BORDER_COLOR),
                margin=ft.Margin(20, 10, 20, 10),
            )
            if page.platform in (ft.PagePlatform.ANDROID, ft.PagePlatform.IOS)
            else ft.Container(),
            ft.Container(height=100),
        ]
    )
