"""Onboarding screen — first-launch swipe-through + Google Sign-In."""

from __future__ import annotations

import logging

import flet as ft

from core import theme, tokens
from core.constants import STORAGE_ONBOARDING_DONE
from state import AppStateCtx
from state.service_ctx import ServiceCtx

from .auth_view import build_auth_slide
from .slides import build_slide_1, build_slide_2

logger = logging.getLogger(__name__)

TOTAL_SLIDES = 3


@ft.component
def OnboardingScreen() -> ft.Control:
    """Build the onboarding swipe-through with mandatory Google Sign-In."""
    state = ft.use_context(AppStateCtx)
    services = ft.use_context(ServiceCtx)
    page = ft.context.page

    slide_index, set_slide_index = ft.use_state(0)
    auth_code, set_auth_code = ft.use_state("")
    auth_status, set_auth_status = ft.use_state("")
    auth_status_color, set_auth_status_color = ft.use_state(theme.SUCCESS)
    is_loading_auth, set_is_loading_auth = ft.use_state(False)
    show_verify, set_show_verify = ft.use_state(False)
    auth_code_ref = ft.use_ref(None)
    is_submitting_ref = ft.use_ref(False)

    async def start_auth(e):
        if not services.colab:
            return
        set_is_loading_auth(True)
        try:
            auth_url = await services.colab.get_auth_url()
            await ft.UrlLauncher().launch_url(auth_url)
            set_show_verify(True)
            set_is_loading_auth(False)
        except Exception as ex:
            logger.error("OAuth URL failed: %s", ex)
            set_auth_status(f"Error: {ex}")
            set_auth_status_color(theme.ERROR)
            set_is_loading_auth(False)

    async def submit_code(e):
        if state.is_authenticated or is_submitting_ref.current:
            return

        code = auth_code.strip()
        if not code and auth_code_ref.current and auth_code_ref.current.value:
            code = auth_code_ref.current.value.strip()
        if not code:
            set_auth_status("Please paste your authorization code first.")
            set_auth_status_color(theme.WARNING)
            return
        if not services.colab:
            return

        is_submitting_ref.current = True
        set_is_loading_auth(True)
        set_auth_status("Verifying...")
        set_auth_status_color(theme.PRIMARY)

        try:
            result = await services.colab.authenticate_oauth2(code)
            if result.get("success"):
                state.is_authenticated = True
                state.colab_authenticated = True
                state.onboarding_done = True
                state.auth_email = result.get("email", "")
                set_auth_status(f"✓ Signed in as {state.auth_email}")
                set_auth_status_color(theme.SUCCESS)
                set_is_loading_auth(False)
            else:
                set_auth_status(f"Failed: {result.get('error', 'Unknown')}")
                set_auth_status_color(theme.ERROR)
                set_is_loading_auth(False)
                is_submitting_ref.current = False
        except Exception as ex:
            set_auth_status(f"Error: {ex}")
            set_auth_status_color(theme.ERROR)
            set_is_loading_auth(False)
            is_submitting_ref.current = False

    def build_slide(index):
        if index == 0:
            return build_slide_1()
        elif index == 1:
            return build_slide_2()
        else:
            return build_auth_slide(
                page=page,
                auth_code=auth_code,
                auth_status=auth_status,
                auth_status_color=auth_status_color,
                is_loading_auth=is_loading_auth,
                show_verify=show_verify,
                auth_code_ref=auth_code_ref,
                start_auth_fn=start_auth,
                submit_code_fn=submit_code,
                set_auth_code_fn=set_auth_code,
            )

    def build_indicators():
        return [
            ft.Container(
                width=8 if i != slide_index else 20,
                height=8,
                border_radius=4,
                bgcolor=theme.PRIMARY
                if i == slide_index
                else ft.Colors.with_opacity(0.3, ft.Colors.ON_SURFACE),
                animate=ft.Animation(200, ft.AnimationCurve.EASE_IN_OUT),
            )
            for i in range(TOTAL_SLIDES)
        ]

    async def on_next(e):
        if slide_index < TOTAL_SLIDES - 1:
            set_slide_index(slide_index + 1)
        else:
            if services.storage:
                await services.storage.set(STORAGE_ONBOARDING_DONE, "true")
            state.is_authenticated = True
            state.onboarding_done = True

    def on_back(e):
        if slide_index > 0:
            set_slide_index(slide_index - 1)

    def on_swipe(e):
        v = e.primary_velocity or 0
        if v < -300 and slide_index < TOTAL_SLIDES - 1:
            set_slide_index(slide_index + 1)
        elif v > 300 and slide_index > 0:
            set_slide_index(slide_index - 1)

    is_last = slide_index == TOTAL_SLIDES - 1
    btn_text = (
        "Get Started"
        if state.is_authenticated
        else "Sign in to continue"
        if is_last
        else "Next"
    )
    btn_disabled = (not state.is_authenticated) if is_last else False

    nav_row = ft.Container(
        content=ft.Row(
            controls=[
                ft.TextButton(
                    content=ft.Text("Back"), on_click=on_back, visible=slide_index > 0
                ),
                ft.Row(controls=build_indicators(), spacing=tokens.SPACE_SM),
                ft.FilledButton(
                    content=ft.Text(btn_text),
                    disabled=btn_disabled,
                    on_click=lambda e: page.run_task(on_next, e) if page else None,
                ),
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        padding=ft.Padding(
            tokens.SPACE_LG, tokens.SPACE_MD, tokens.SPACE_LG, tokens.SPACE_XL
        ),
    )

    slide_area = ft.GestureDetector(
        content=ft.Container(
            content=build_slide(slide_index),
            expand=True,
            padding=ft.Padding(tokens.SPACE_XL, 0, tokens.SPACE_XL, 0),
        ),
        on_horizontal_drag_end=on_swipe,
    )

    return ft.SafeArea(
        content=ft.Column(
            controls=[slide_area, nav_row],
            expand=True,
            spacing=0,
        ),
        expand=True,
    )


__all__ = ["OnboardingScreen"]
