"""Shimmer loading skeletons for InsightCard."""

from __future__ import annotations

import flet as ft

from core import tokens


def shimmer_bar(
    width=None,
    height=tokens.SPACE_MD,
    radius=tokens.RADIUS_SHIMMER,
    expand=False,
) -> ft.Shimmer:
    """One shimmering skeleton bar (loading placeholder)."""
    return ft.Shimmer(
        content=ft.Container(
            width=width,
            height=height,
            border_radius=radius,
            expand=expand,
            bgcolor=ft.Colors.with_opacity(tokens.OPACITY_LIGHT, ft.Colors.ON_SURFACE),
        ),
        base_color=ft.Colors.with_opacity(tokens.OPACITY_SUBTLE, ft.Colors.ON_SURFACE),
        highlight_color=ft.Colors.with_opacity(
            tokens.OPACITY_HIGHLIGHT, ft.Colors.ON_SURFACE
        ),
        period=tokens.SHIMMER_PERIOD_MS,
    )


def build_running_skeleton() -> ft.Control:
    """Shimmering placeholder shown while a cell executes on Colab."""
    header = ft.Row(
        [
            ft.ProgressRing(
                width=tokens.PROGRESS_RING_XS,
                height=tokens.PROGRESS_RING_XS,
                stroke_width=tokens.PROGRESS_RING_STROKE_THIN,
            ),
            ft.Text(
                "Executing analysis code…",
                size=tokens.FONT_XS,
                color=ft.Colors.ON_SURFACE_VARIANT,
            ),
        ],
        spacing=tokens.SPACE_SM,
    )
    skeleton = ft.Column(
        [
            ft.Row(
                [
                    shimmer_bar(120, tokens.SPACE_LG, tokens.RADIUS_SM),
                    shimmer_bar(70, tokens.SPACE_LG, tokens.RADIUS_SM),
                ],
                spacing=tokens.SPACE_SM,
                alignment=ft.MainAxisAlignment.END,
            ),
            shimmer_bar(height=tokens.FONT_MD),
            shimmer_bar(height=tokens.FONT_MD),
            shimmer_bar(width=180, height=tokens.FONT_MD),
            ft.Row(
                [
                    shimmer_bar(
                        tokens.INPUT_WIDTH_MD,
                        tokens.INPUT_WIDTH_MD,
                        tokens.RADIUS_MD,
                    ),
                    shimmer_bar(
                        expand=True,
                        height=tokens.INPUT_WIDTH_MD,
                        radius=tokens.RADIUS_MD,
                    ),
                ],
                spacing=tokens.SPACE_SM,
            ),
        ],
        spacing=tokens.SPACE_SM,
    )
    return ft.Container(
        content=ft.Column([header, skeleton], spacing=tokens.SPACE_SM),
        padding=tokens.SPACE_SM,
    )
