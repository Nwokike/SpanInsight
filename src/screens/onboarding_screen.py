"""Onboarding view — first-launch swipe-through + Google Sign-In.

Shows 3 slides:
  1. Welcome + key features
  2. How it works (Colab-powered)
  3. Google Sign-In (mandatory — app cannot function without Colab auth)

Cannot be dismissed until the user has authenticated.
STORAGE_ONBOARDING_DONE is set only after successful sign-in.
"""

from __future__ import annotations

import logging

import flet as ft

from core import theme, tokens
from core.constants import STORAGE_ONBOARDING_DONE
from state import AppStateCtx
from state.service_ctx import ServiceCtx

logger = logging.getLogger(__name__)

TOTAL_SLIDES = 3


@ft.component
def OnboardingScreen() -> ft.Control:
    """Build the onboarding swipe-through with mandatory Google Sign-In."""
    state = ft.use_context(AppStateCtx)
    services = ft.use_context(ServiceCtx)
    page = ft.context.page

    slide_index, set_slide_index = ft.use_state(0)
    auth_code, _set_auth_code = ft.use_state("")
    auth_status, set_auth_status = ft.use_state("")
    auth_status_color, set_auth_status_color = ft.use_state(theme.SUCCESS)
    is_loading_auth, set_is_loading_auth = ft.use_state(False)
    show_verify, set_show_verify = ft.use_state(False)
    auth_code_ref = ft.use_ref(None)
    is_submitting_ref = ft.use_ref(False)

    # ── Auth handlers ───────────────────────────────────────────
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

        code = (
            auth_code_ref.current.value.strip()
            if auth_code_ref.current and auth_code_ref.current.value
            else auth_code.strip()
        )
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

    # ── Slide builders ──────────────────────────────────────────
    def _feature_row(icon, title, subtitle):
        return ft.Container(
            content=ft.Row(
                controls=[
                    ft.Container(
                        content=ft.Icon(icon, size=22, color=theme.PRIMARY),
                        width=40,
                        height=40,
                        border_radius=10,
                        bgcolor=ft.Colors.with_opacity(0.1, theme.PRIMARY),
                        alignment=ft.Alignment.CENTER,
                    ),
                    ft.Column(
                        controls=[
                            ft.Text(
                                title, size=tokens.FONT_LG, weight=ft.FontWeight.W_600
                            ),
                            ft.Text(
                                subtitle,
                                size=tokens.FONT_SM,
                                color=ft.Colors.ON_SURFACE_VARIANT,
                            ),
                        ],
                        spacing=tokens.SPACE_XXS,
                        expand=True,
                    ),
                ],
                spacing=tokens.SPACE_MD,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            padding=ft.Padding(0, tokens.SPACE_SM, 0, tokens.SPACE_SM),
        )

    def build_slide_1():
        from components.brand_header import build_brand_header

        return ft.Column(
            controls=[
                build_brand_header(show_tagline=True, spacing_below=True),
                _feature_row(
                    ft.Icons.AUTO_AWESOME_ROUNDED,
                    "Smart Analysis",
                    "Upload data, describe what you need — charts and insights appear automatically",
                ),
                _feature_row(
                    ft.Icons.MEMORY_ROUNDED,
                    "Cloud-Powered",
                    "Runs on cloud compute — free CPU, GPU, TPU and unlimited packages",
                ),
                _feature_row(
                    ft.Icons.DYNAMIC_FORM_ROUNDED,
                    "Smart Surveys",
                    "Create forms in plain English, share and collect responses",
                ),
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=tokens.SPACE_SM,
        )

    def build_slide_2():
        return ft.Column(
            controls=[
                ft.Container(height=tokens.SPACE_XL),
                ft.Icon(ft.Icons.ROCKET_LAUNCH_ROUNDED, size=56, color=theme.PRIMARY),
                ft.Text(
                    "How It Works",
                    size=24,
                    weight=ft.FontWeight.W_700,
                    text_align=ft.TextAlign.CENTER,
                ),
                ft.Container(height=tokens.SPACE_SM),
                _feature_row(
                    ft.Icons.ADD_CIRCLE_OUTLINE_ROUNDED,
                    "1. Connect Session",
                    "Start CPU (free), GPU (T4/L4/A100/H100), or TPU (v5e1 free, v6e1 Pro) sessions",
                ),
                _feature_row(
                    ft.Icons.NOTE_ADD_ROUNDED,
                    "2. Upload Data",
                    "Send CSV, Excel, or any file to your cloud runtime",
                ),
                _feature_row(
                    ft.Icons.EDIT_NOTE_ROUNDED,
                    "3. Describe Your Analysis",
                    "Tell SpanInsight what you want in plain English, or use Autopilot",
                ),
                _feature_row(
                    ft.Icons.DOWNLOAD_ROUNDED,
                    "4. Export",
                    "Save reports or download .ipynb notebooks",
                ),
                ft.Container(height=tokens.SPACE_SM),
                ft.Container(
                    content=ft.Text(
                        "💡 CPU, T4 GPU, and TPU v5e1 are free. L4/G4 require Pro, A100/H100/v6e1 require Pro+.",
                        size=tokens.FONT_SM,
                        color=ft.Colors.ON_SURFACE_VARIANT,
                        text_align=ft.TextAlign.CENTER,
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
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=tokens.SPACE_SM,
        )

    def build_slide_3():
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
                    on_click=lambda e: page.run_task(start_auth, e),
                ),
                ft.TextField(
                    ref=auth_code_ref,
                    label="Paste authorization code",
                    prefix_icon=ft.Icons.KEY_ROUNDED,
                    border_radius=tokens.RADIUS_MD,
                    text_size=tokens.FONT_MD,
                    visible=show_verify,
                    on_submit=lambda e: page.run_task(submit_code, e),
                ),
                ft.FilledTonalButton(
                    content=ft.Text("Verify Code"),
                    icon=ft.Icons.VERIFIED_ROUNDED,
                    visible=show_verify,
                    disabled=is_loading_auth,
                    on_click=lambda e: page.run_task(submit_code, e),
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

    # ── Navigation ──────────────────────────────────────────────
    def build_slide(index):
        return [build_slide_1, build_slide_2, build_slide_3][index]()

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
            # Only reachable when authenticated (button is disabled otherwise)
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

    # ── Layout ──────────────────────────────────────────────────
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
                    on_click=lambda e: page.run_task(on_next, e),
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
