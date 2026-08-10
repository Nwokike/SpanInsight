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
from collections.abc import Callable

import flet as ft

from core import theme, tokens
from core.constants import STORAGE_ONBOARDING_DONE
from core.state import state

logger = logging.getLogger(__name__)

TOTAL_SLIDES = 3


def build_onboarding_view(
    page: ft.Page,
    on_done: Callable,
    storage=None,
    colab_service=None,
) -> ft.View:
    """Build the onboarding swipe-through with mandatory Google Sign-In."""

    current = {"index": 0}
    indicator_row = ft.Ref[ft.Row]()
    slide_ref = ft.Ref[ft.Container]()
    next_btn = ft.Ref[ft.FilledButton]()
    back_btn = ft.Ref[ft.TextButton]()

    # Auth refs for slide 3
    sign_in_btn = ft.Ref[ft.FilledButton]()
    auth_code_field = ft.Ref[ft.TextField]()
    auth_status_text = ft.Ref[ft.Text]()
    verify_btn = ft.Ref[ft.FilledTonalButton]()

    # ── Auth handlers ───────────────────────────────────────────
    async def start_auth(e):
        if not colab_service:
            return
        if sign_in_btn.current:
            sign_in_btn.current.disabled = True
            sign_in_btn.current.update()

        try:
            auth_url = await colab_service.get_auth_url()
            await ft.UrlLauncher().launch_url(auth_url)
            if auth_code_field.current:
                auth_code_field.current.visible = True
            if verify_btn.current:
                verify_btn.current.visible = True
            page.update()
        except Exception as ex:
            logger.error("OAuth URL failed: %s", ex)
            if auth_status_text.current:
                auth_status_text.current.value = f"Error: {ex}"
                auth_status_text.current.color = theme.ERROR
                auth_status_text.current.visible = True
            if sign_in_btn.current:
                sign_in_btn.current.disabled = False
            page.update()

    async def submit_code(e):
        code = auth_code_field.current.value.strip() if auth_code_field.current else ""
        if not code or not colab_service:
            return
        if verify_btn.current:
            verify_btn.current.disabled = True
        if auth_status_text.current:
            auth_status_text.current.value = "Verifying..."
            auth_status_text.current.color = theme.PRIMARY
            auth_status_text.current.visible = True
        page.update()

        try:
            result = await colab_service.authenticate_oauth2(code)
            if result.get("success"):
                state.is_authenticated = True
                state.colab_authenticated = True
                state.auth_email = result.get("email", "")
                if auth_status_text.current:
                    auth_status_text.current.value = (
                        f"✓ Signed in as {state.auth_email}"
                    )
                    auth_status_text.current.color = theme.SUCCESS
                # Enable the Get Started button now that auth succeeded
                if next_btn.current:
                    next_btn.current.content = ft.Text("Get Started")
                    next_btn.current.disabled = False
            else:
                if auth_status_text.current:
                    auth_status_text.current.value = (
                        f"Failed: {result.get('error', 'Unknown')}"
                    )
                    auth_status_text.current.color = theme.ERROR
                if verify_btn.current:
                    verify_btn.current.disabled = False
        except Exception as ex:
            if auth_status_text.current:
                auth_status_text.current.value = f"Error: {ex}"
                auth_status_text.current.color = theme.ERROR
            if verify_btn.current:
                verify_btn.current.disabled = False
        page.update()

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
                            ft.Text("Cloud CLI ready", size=tokens.FONT_SM),
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
                    ref=sign_in_btn,
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
                    on_click=lambda e: page.run_task(start_auth, e),
                ),
                ft.TextField(
                    ref=auth_code_field,
                    label="Paste authorization code",
                    prefix_icon=ft.Icons.KEY_ROUNDED,
                    border_radius=tokens.RADIUS_MD,
                    text_size=tokens.FONT_MD,
                    visible=False,
                    on_submit=lambda e: page.run_task(submit_code, e),
                ),
                ft.FilledTonalButton(
                    content=ft.Text("Verify Code"),
                    ref=verify_btn,
                    icon=ft.Icons.VERIFIED_ROUNDED,
                    visible=False,
                    on_click=lambda e: page.run_task(submit_code, e),
                ),
                ft.Text(
                    ref=auth_status_text,
                    value="",
                    size=tokens.FONT_SM,
                    color=theme.SUCCESS,
                    text_align=ft.TextAlign.CENTER,
                    visible=False,
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
                width=8 if i != current["index"] else 20,
                height=8,
                border_radius=4,
                bgcolor=theme.PRIMARY
                if i == current["index"]
                else ft.Colors.with_opacity(0.3, ft.Colors.ON_SURFACE),
                animate=ft.Animation(200, ft.AnimationCurve.EASE_IN_OUT),
            )
            for i in range(TOTAL_SLIDES)
        ]

    def update_view():
        i = current["index"]
        if slide_ref.current:
            slide_ref.current.content = build_slide(i)
        if indicator_row.current:
            indicator_row.current.controls = build_indicators()
        if back_btn.current:
            back_btn.current.visible = i > 0
        if next_btn.current:
            if i == TOTAL_SLIDES - 1:
                # On the auth slide: button is disabled until authenticated
                next_btn.current.content = ft.Text(
                    "Get Started" if state.is_authenticated else "Sign in to continue"
                )
                next_btn.current.disabled = not state.is_authenticated
            else:
                next_btn.current.content = ft.Text("Next")
                next_btn.current.disabled = False
        page.update()

    async def on_next(e):
        if current["index"] < TOTAL_SLIDES - 1:
            current["index"] += 1
            update_view()
        else:
            # Only reachable when authenticated (button is disabled otherwise)
            if storage:
                await storage.set(STORAGE_ONBOARDING_DONE, "true")
            on_done()

    def on_back(e):
        if current["index"] > 0:
            current["index"] -= 1
            update_view()

    def on_swipe(e):
        v = e.primary_velocity or 0
        if v < -300 and current["index"] < TOTAL_SLIDES - 1:
            current["index"] += 1
            update_view()
        elif v > 300 and current["index"] > 0:
            current["index"] -= 1
            update_view()

    # ── Layout ──────────────────────────────────────────────────
    nav_row = ft.Container(
        content=ft.Row(
            controls=[
                ft.TextButton(
                    content=ft.Text("Back"),
                    ref=back_btn,
                    on_click=on_back,
                    visible=False,
                ),
                ft.Row(
                    ref=indicator_row,
                    controls=build_indicators(),
                    spacing=tokens.SPACE_SM,
                ),
                ft.FilledButton(
                    content=ft.Text("Next"),
                    ref=next_btn,
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
            ref=slide_ref,
            content=build_slide(0),
            expand=True,
            padding=ft.Padding(tokens.SPACE_XL, 0, tokens.SPACE_XL, 0),
        ),
        on_horizontal_drag_end=on_swipe,
    )

    return ft.View(
        route="/onboarding",
        controls=[
            ft.SafeArea(
                content=ft.Column(
                    controls=[slide_area, nav_row],
                    expand=True,
                    spacing=0,
                ),
                expand=True,
            )
        ],
        padding=0,
        # No navigation_bar — onboarding is a standalone full-screen flow
    )
