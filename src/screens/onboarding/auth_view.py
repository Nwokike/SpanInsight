"""Google Sign-In authentication slide for onboarding."""

from __future__ import annotations

import flet as ft

from core import theme, tokens


def build_auth_slide(
    page: ft.Page,
    auth_code: str,
    auth_status: str,
    auth_status_color: str,
    is_loading_auth: bool,
    show_verify: bool,
    auth_code_ref: ft.Ref,
    start_auth_fn,
    submit_code_fn,
    set_auth_code_fn,
) -> ft.Column:
    """Build Slide 3: Google Sign-In with OAuth verification."""
    return ft.Column(
        controls=[
            ft.Container(height=tokens.SPACE_XL),
            ft.Icon(ft.Icons.LOCK_OPEN_ROUNDED, size=56, color=theme.PRIMARY),
            ft.Text(
                "Sign in to Google",
                size=24,
                weight=ft.FontWeight.W_700,
                text_align=ft.TextAlign.CENTER,
            ),
            ft.Text(
                "Required to create and manage analysis sessions",
                size=tokens.FONT_SM,
                color=ft.Colors.ON_SURFACE_VARIANT,
                text_align=ft.TextAlign.CENTER,
            ),
            ft.Container(height=tokens.SPACE_LG),
            ft.Container(
                content=ft.Row(
                    controls=[
                        ft.Icon(
                            ft.Icons.CHECK_CIRCLE_ROUNDED,
                            size=16,
                            color=theme.SUCCESS,
                        ),
                        ft.Text("Colab CLI ready", size=tokens.FONT_SM),
                    ],
                    spacing=tokens.SPACE_SM,
                ),
                padding=ft.Padding(
                    tokens.SPACE_LG,
                    tokens.SPACE_MD,
                    tokens.SPACE_LG,
                    tokens.SPACE_MD,
                ),
                bgcolor=ft.Colors.with_opacity(0.05, ft.Colors.ON_SURFACE),
                border_radius=tokens.RADIUS_MD,
            ),
            ft.Container(height=tokens.SPACE_LG),
            ft.Text(
                "💡 IMPORTANT: A browser will open. After copying the code, close it and return here.",
                size=tokens.FONT_XS,
                color=theme.WARNING,
                text_align=ft.TextAlign.CENTER,
            ),
            ft.Container(height=tokens.SPACE_SM),
            ft.FilledButton(
                content=ft.Text("Sign in with Google"),
                icon=ft.Icons.LOGIN_ROUNDED,
                width=float("inf"),
                style=ft.ButtonStyle(
                    padding=ft.Padding(
                        tokens.SPACE_XL,
                        tokens.SPACE_MD,
                        tokens.SPACE_XL,
                        tokens.SPACE_MD,
                    ),
                ),
                disabled=is_loading_auth,
                on_click=lambda e: page.run_task(start_auth_fn, e)
                if page
                else None,
            ),
            ft.TextField(
                ref=auth_code_ref,
                value=auth_code,
                label="Paste authorization code",
                prefix_icon=ft.Icons.KEY_ROUNDED,
                border_radius=tokens.RADIUS_MD,
                text_size=tokens.FONT_MD,
                visible=show_verify,
                on_change=lambda e: set_auth_code_fn(e.control.value),
                on_submit=lambda e: page.run_task(submit_code_fn, e)
                if page
                else None,
            ),
            ft.FilledTonalButton(
                content=ft.Text("Verify Code"),
                icon=ft.Icons.VERIFIED_ROUNDED,
                visible=show_verify,
                disabled=is_loading_auth,
                on_click=lambda e: page.run_task(submit_code_fn, e)
                if page
                else None,
            ),
            ft.Text(
                value=auth_status,
                size=tokens.FONT_SM,
                color=auth_status_color,
                text_align=ft.TextAlign.CENTER,
                visible=bool(auth_status),
            ),
            ft.Divider(height=tokens.SPACE_SM),
            ft.Text(
                "Disclaimer: Unofficial client. Not affiliated with Google LLC.",
                size=tokens.FONT_XXS,
                color=ft.Colors.ON_SURFACE_VARIANT,
                text_align=ft.TextAlign.CENTER,
                italic=True,
            ),
        ],
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        spacing=tokens.SPACE_SM,
    )
