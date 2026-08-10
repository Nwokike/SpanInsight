"""Home view v2 — dashboard with Colab session status and quick actions.

Evolved from v1: removes workspace/project cards (simplified),
adds Colab connection status, updates narrative from "local-only" to "cloud-powered".
"""

from __future__ import annotations

import logging
from collections.abc import Callable

import flet as ft

from components.brand_header import build_brand_header
from core import theme, tokens
from core.state import state

logger = logging.getLogger(__name__)


def build_home_view(
    page: ft.Page,
    on_start_analysis: Callable,
    on_navigate: Callable,
    storage=None,
    colab_service=None,
) -> ft.View:
    """Build the Home landing tab."""

    # ── Colab status bar ────────────────────────────────────────
    def _colab_status_bar() -> ft.Container:
        if state.colab_connected:
            return ft.Container(
                content=ft.Row(
                    controls=[
                        ft.Icon(
                            ft.Icons.CLOUD_DONE_ROUNDED, size=14, color=theme.SUCCESS
                        ),
                        ft.Text(
                            f"Colab connected — {state.session_hardware}",
                            size=tokens.FONT_XS,
                            color=theme.SUCCESS,
                            weight=ft.FontWeight.W_600,
                        ),
                    ],
                    spacing=tokens.SPACE_SM,
                    alignment=ft.MainAxisAlignment.CENTER,
                ),
                padding=ft.Padding(0, 8, 0, 8),
                bgcolor=ft.Colors.with_opacity(0.06, theme.SUCCESS),
                border=ft.Border(
                    bottom=ft.BorderSide(1, ft.Colors.with_opacity(0.15, theme.SUCCESS))
                ),
            )
        elif not state.gateway_online:
            return ft.Container(
                content=ft.Row(
                    controls=[
                        ft.Icon(
                            ft.Icons.WIFI_OFF_ROUNDED, size=14, color=theme.WARNING
                        ),
                        ft.Text(
                            "No internet connection",
                            size=tokens.FONT_XS,
                            weight=ft.FontWeight.W_500,
                            color=theme.WARNING,
                        ),
                    ],
                    spacing=tokens.SPACE_SM,
                    alignment=ft.MainAxisAlignment.CENTER,
                ),
                padding=ft.Padding(0, 8, 0, 8),
                bgcolor=ft.Colors.with_opacity(0.08, theme.WARNING),
                border=ft.Border(
                    bottom=ft.BorderSide(1, ft.Colors.with_opacity(0.15, theme.WARNING))
                ),
            )
        else:
            return ft.Container()

    # ── Hero ────────────────────────────────────────────────────
    hero = build_brand_header(show_tagline=True, spacing_below=True)

    # ── Quick actions ───────────────────────────────────────────
    quick_actions = ft.Container(
        content=ft.Column(
            controls=[
                ft.Text(
                    "Quick Start",
                    size=tokens.FONT_MD,
                    weight=ft.FontWeight.W_600,
                ),
                ft.Container(height=tokens.SPACE_SM),
                ft.Row(
                    controls=[
                        _action_card(
                            icon=ft.Icons.AUTO_AWESOME_ROUNDED,
                            title="Analyze Data",
                            subtitle="AI + Colab",
                            color=theme.PRIMARY,
                            on_click=lambda e: on_start_analysis(e, autopilot=False),
                        ),
                        _action_card(
                            icon=ft.Icons.ROCKET_LAUNCH_ROUNDED,
                            title="Autopilot",
                            subtitle="Auto-report",
                            color=theme.ACCENT,
                            on_click=lambda e: on_start_analysis(e, autopilot=True),
                        ),
                    ],
                    spacing=tokens.SPACE_MD,
                ),
                ft.Container(height=tokens.SPACE_SM),
                ft.Row(
                    controls=[
                        _action_card(
                            icon=ft.Icons.DYNAMIC_FORM_ROUNDED,
                            title="Surveys",
                            subtitle="AI forms",
                            color=theme.WARNING,
                            on_click=lambda e: on_navigate("/forms"),
                        ),
                        _action_card(
                            icon=ft.Icons.ASSESSMENT_ROUNDED,
                            title="Reports",
                            subtitle=f"{len(state.user_reports or [])} saved",
                            color=theme.SUCCESS,
                            on_click=lambda e: on_navigate("/reports"),
                        ),
                    ],
                    spacing=tokens.SPACE_MD,
                ),
            ],
            spacing=0,
        ),
        padding=ft.Padding(tokens.SPACE_LG, 0, tokens.SPACE_LG, tokens.SPACE_LG),
    )

    # ── Cloud power banner ──────────────────────────────────────
    cloud_banner = ft.Container(
        content=ft.Row(
            controls=[
                ft.Icon(
                    ft.Icons.MEMORY_ROUNDED, size=tokens.ICON_MD, color=theme.PRIMARY
                ),
                ft.Column(
                    controls=[
                        ft.Text(
                            "Colab-Powered Analysis",
                            size=tokens.FONT_SM,
                            weight=ft.FontWeight.W_600,
                        ),
                        ft.Text(
                            "Your data runs on Google Colab's GPU/TPU VMs. "
                            "No local limits — use pandas, scikit-learn, "
                            "TensorFlow, and more.",
                            size=tokens.FONT_XS,
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
        padding=ft.Padding(
            tokens.SPACE_LG, tokens.SPACE_MD, tokens.SPACE_LG, tokens.SPACE_MD
        ),
        margin=ft.Margin(
            tokens.SPACE_LG, tokens.SPACE_SM, tokens.SPACE_LG, tokens.SPACE_SM
        ),
        border_radius=tokens.RADIUS_LG,
        bgcolor=ft.Colors.with_opacity(0.06, theme.PRIMARY),
        border=ft.Border.all(1, ft.Colors.with_opacity(0.15, theme.PRIMARY)),
    )

    # ── Features ────────────────────────────────────────────────
    features = ft.Container(
        content=ft.Column(
            controls=[
                ft.Text(
                    "What SpanInsight Does",
                    size=tokens.FONT_MD,
                    weight=ft.FontWeight.W_600,
                ),
                ft.Container(height=tokens.SPACE_SM),
                _feature_card(
                    ft.Icons.AUTO_AWESOME_ROUNDED,
                    "AI-Powered Analysis",
                    "Upload any dataset. AI writes Python code and runs it on "
                    "Colab — generating charts, ML models, and statistical insights.",
                    theme.PRIMARY,
                ),
                _feature_card(
                    ft.Icons.DYNAMIC_FORM_ROUNDED,
                    "Smart Surveys",
                    "Describe a questionnaire in plain English. AI generates it. "
                    "Share a link, collect responses, and analyze results.",
                    theme.WARNING,
                ),
                _feature_card(
                    ft.Icons.ROCKET_LAUNCH_ROUNDED,
                    "Autopilot Mode",
                    "One tap. AI runs multiple analysis passes on Colab, "
                    "generates charts, and builds a complete report.",
                    theme.ACCENT,
                ),
                _feature_card(
                    ft.Icons.CODE_ROUNDED,
                    "Expert Code Mode",
                    "Toggle to code mode and write Python directly. "
                    "Full Colab runtime at your fingertips — install any package.",
                    theme.SUCCESS,
                ),
            ],
            spacing=tokens.SPACE_MD,
        ),
        padding=ft.Padding(
            tokens.SPACE_LG, tokens.SPACE_LG, tokens.SPACE_LG, tokens.SPACE_SM
        ),
    )

    # ── How it works ────────────────────────────────────────────
    how_it_works = ft.Container(
        content=ft.Column(
            controls=[
                ft.Text(
                    "How It Works",
                    size=tokens.FONT_MD,
                    weight=ft.FontWeight.W_600,
                ),
                ft.Container(height=tokens.SPACE_SM),
                _step_row("1", "Connect", "Sign in to Google Colab in one tap"),
                _step_row("2", "Upload", "Send your data file to Colab's cloud VM"),
                _step_row("3", "Analyze", "Ask questions or let Autopilot run"),
                _step_row("4", "Export", "Save as .ipynb or share via Google Drive"),
            ],
            spacing=tokens.SPACE_MD,
        ),
        padding=ft.Padding(
            tokens.SPACE_LG, tokens.SPACE_LG, tokens.SPACE_LG, tokens.SPACE_SM
        ),
    )

    # ── Credits info ────────────────────────────────────────────
    credits_info = ft.Container(
        content=ft.Row(
            controls=[
                ft.Icon(ft.Icons.BOLT_ROUNDED, size=20, color=theme.ACCENT),
                ft.Column(
                    [
                        ft.Text(
                            "50 Free Credits Daily",
                            size=tokens.FONT_SM,
                            weight=ft.FontWeight.W_600,
                        ),
                        ft.Text(
                            "Each AI analysis costs 1 credit. Resets at midnight UTC.",
                            size=tokens.FONT_XS,
                            color=ft.Colors.ON_SURFACE_VARIANT,
                        ),
                    ],
                    spacing=2,
                    expand=True,
                ),
            ],
            spacing=tokens.SPACE_MD,
            vertical_alignment="center",
        ),
        padding=ft.Padding(
            tokens.SPACE_LG, tokens.SPACE_MD, tokens.SPACE_LG, tokens.SPACE_MD
        ),
        margin=ft.Margin(tokens.SPACE_LG, 0, tokens.SPACE_LG, tokens.SPACE_LG),
        border_radius=tokens.RADIUS_LG,
        bgcolor=ft.Colors.with_opacity(0.06, theme.ACCENT),
        border=ft.Border.all(1, ft.Colors.with_opacity(0.15, theme.ACCENT)),
    )

    # ── Ad helper ───────────────────────────────────────────────
    def _create_home_ad() -> ft.Control:
        if page.platform in (ft.PagePlatform.ANDROID, ft.PagePlatform.IOS):
            try:
                import flet_ads as fta

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
                            fta.BannerAd(
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
                    border_radius=tokens.RADIUS_LG,
                    bgcolor=theme.GLASS_BG,
                    border=ft.Border.all(1, theme.GLASS_BORDER_COLOR),
                    margin=ft.Margin(
                        tokens.SPACE_LG, 0, tokens.SPACE_LG, tokens.SPACE_LG
                    ),
                )
            except Exception:
                pass
        return ft.Container()

    # ── Layout ──────────────────────────────────────────────────
    content = ft.Column(
        controls=[
            _colab_status_bar(),
            hero,
            quick_actions,
            _create_home_ad(),
            cloud_banner,
            features,
            _create_home_ad(),
            how_it_works,
            credits_info,
            ft.Container(height=80),
        ],
        scroll=ft.ScrollMode.AUTO,
        expand=True,
        spacing=0,
    )

    appbar = ft.AppBar(
        title=ft.Text("Home", weight=ft.FontWeight.W_600, size=tokens.FONT_XL),
        center_title=False,
        bgcolor=ft.Colors.TRANSPARENT,
    )

    return ft.View(route="/home", appbar=appbar, controls=[content], padding=0)


def _action_card(
    icon: str, title: str, subtitle: str, color: str, on_click=None
) -> ft.Container:
    """Compact quick action card."""
    return ft.Container(
        content=ft.Column(
            controls=[
                ft.Container(
                    content=ft.Icon(icon, size=tokens.ICON_XL, color=color),
                    width=48,
                    height=48,
                    border_radius=tokens.RADIUS_MD,
                    bgcolor=ft.Colors.with_opacity(0.1, color),
                    alignment=ft.Alignment.CENTER,
                ),
                ft.Text(title, size=tokens.FONT_SM, weight=ft.FontWeight.W_600),
                ft.Text(
                    subtitle, size=tokens.FONT_XXS, color=ft.Colors.ON_SURFACE_VARIANT
                ),
            ],
            spacing=tokens.SPACE_XS,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        expand=True,
        padding=tokens.SPACE_MD,
        border_radius=tokens.RADIUS_LG,
        bgcolor=theme.GLASS_BG,
        border=ft.Border.all(1, theme.GLASS_BORDER_COLOR),
        on_click=on_click,
        ink=True,
    )


def _feature_card(icon: str, title: str, desc: str, color: str) -> ft.Container:
    """Marketing feature card."""
    return ft.Container(
        content=ft.Row(
            controls=[
                ft.Container(
                    content=ft.Icon(icon, size=22, color=color),
                    width=40,
                    height=40,
                    border_radius=10,
                    bgcolor=ft.Colors.with_opacity(0.1, color),
                    alignment=ft.Alignment.CENTER,
                ),
                ft.Column(
                    controls=[
                        ft.Text(title, size=tokens.FONT_SM, weight=ft.FontWeight.W_600),
                        ft.Text(
                            desc,
                            size=tokens.FONT_XS,
                            color=ft.Colors.ON_SURFACE_VARIANT,
                            max_lines=3,
                            overflow="ellipsis",
                        ),
                    ],
                    spacing=2,
                    expand=True,
                ),
            ],
            spacing=tokens.SPACE_MD,
            vertical_alignment="start",
        ),
        padding=12,
        border_radius=10,
        bgcolor=theme.GLASS_BG,
        border=ft.Border.all(1, theme.GLASS_BORDER_COLOR),
    )


def _step_row(number: str, title: str, desc: str) -> ft.Row:
    """Numbered step row."""
    return ft.Row(
        controls=[
            ft.Container(
                content=ft.Text(
                    number,
                    size=tokens.FONT_SM,
                    weight=ft.FontWeight.W_700,
                    color=ft.Colors.WHITE,
                    text_align=ft.TextAlign.CENTER,
                ),
                width=26,
                height=26,
                border_radius=13,
                bgcolor=theme.PRIMARY,
                alignment=ft.Alignment.CENTER,
            ),
            ft.Column(
                controls=[
                    ft.Text(title, size=tokens.FONT_SM, weight=ft.FontWeight.W_600),
                    ft.Text(
                        desc,
                        size=tokens.FONT_XS,
                        color=ft.Colors.ON_SURFACE_VARIANT,
                    ),
                ],
                spacing=tokens.SPACE_XXS,
                expand=True,
            ),
        ],
        spacing=tokens.SPACE_MD,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
    )
