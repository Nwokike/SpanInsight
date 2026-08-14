"""Google account and Colab OAuth2 auth section for Settings."""

from __future__ import annotations

import flet as ft

from core.styles import section_header, setting_tile


def build_auth_section(
    state,
    on_check_auth,
    on_sign_out,
) -> list[ft.Control]:
    """Account verification and sign out tiles."""
    controls = [
        section_header("Google Account"),
        setting_tile(
            icon=ft.Icons.ACCOUNT_CIRCLE_ROUNDED,
            title=state.auth_email or "Not signed in",
            subtitle="Colab OAuth2 — tap to verify"
            if state.is_authenticated
            else "Sign in from onboarding",
            on_click=on_check_auth,
        ),
    ]
    if state.is_authenticated:
        controls.append(
            setting_tile(
                icon=ft.Icons.LOGOUT_ROUNDED,
                title="Sign Out",
                subtitle="Disconnect Google account",
                on_click=on_sign_out,
            )
        )
    return controls
