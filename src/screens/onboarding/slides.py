"""Introductory slides for the onboarding screen."""

from __future__ import annotations

import flet as ft

from components.brand_header import build_brand_header
from core import theme, tokens


def feature_row(icon, title, subtitle) -> ft.Container:
    """Build one icon + title + description row for onboarding slides."""
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


def build_slide_1() -> ft.Column:
    """Slide 1: App overview & key features."""
    return ft.Column(
        controls=[
            build_brand_header(show_tagline=True, spacing_below=True),
            feature_row(
                ft.Icons.AUTO_AWESOME_ROUNDED,
                "Smart Analysis",
                "Upload data, describe what you need — charts and insights appear automatically",
            ),
            feature_row(
                ft.Icons.MEMORY_ROUNDED,
                "Cloud-Powered",
                "Runs on cloud compute — free CPU, GPU, TPU and unlimited packages",
            ),
            feature_row(
                ft.Icons.DYNAMIC_FORM_ROUNDED,
                "Smart Surveys",
                "Create forms in plain English, share and collect responses",
            ),
        ],
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        spacing=tokens.SPACE_SM,
    )


def build_slide_2() -> ft.Column:
    """Slide 2: How the cloud runtime works."""
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
            feature_row(
                ft.Icons.ADD_CIRCLE_OUTLINE_ROUNDED,
                "1. Connect Session",
                "Start CPU (free), GPU (T4/L4/A100/H100), or TPU (v5e1 free, v6e1 Pro) sessions",
            ),
            feature_row(
                ft.Icons.NOTE_ADD_ROUNDED,
                "2. Upload Data",
                "Send CSV, Excel, or any file to your cloud runtime",
            ),
            feature_row(
                ft.Icons.EDIT_NOTE_ROUNDED,
                "3. Describe Your Analysis",
                "Tell SpanInsight what you want in plain English, or use Autopilot",
            ),
            feature_row(
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
