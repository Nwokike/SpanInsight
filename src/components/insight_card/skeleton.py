"""Shimmer loading skeletons for InsightCard."""

from __future__ import annotations

import flet as ft

from core import tokens


def shimmer_bar(width=None, height=12, radius=6, expand=False) -> ft.Shimmer:
    """One shimmering skeleton bar (loading placeholder)."""
    return ft.Shimmer(
        content=ft.Container(
            width=width,
            height=height,
            border_radius=radius,
            expand=expand,
            bgcolor=ft.Colors.with_opacity(0.10, ft.Colors.ON_SURFACE),
        ),
        base_color=ft.Colors.with_opacity(0.06, ft.Colors.ON_SURFACE),
        highlight_color=ft.Colors.with_opacity(0.22, ft.Colors.ON_SURFACE),
        period=1200,
    )


def build_running_skeleton() -> ft.Control:
    """Shimmering placeholder shown while a cell executes on Colab."""
    header = ft.Row(
        [
            ft.ProgressRing(width=14, height=14, stroke_width=2),
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
                    shimmer_bar(120, 16, 8),
                    shimmer_bar(70, 16, 8),
                ],
                spacing=tokens.SPACE_SM,
                alignment=ft.MainAxisAlignment.END,
            ),
            shimmer_bar(height=14),
            shimmer_bar(height=14),
            shimmer_bar(width=180, height=14),
            ft.Row(
                [
                    shimmer_bar(110, 110, tokens.RADIUS_MD),
                    shimmer_bar(expand=True, height=110, radius=tokens.RADIUS_MD),
                ],
                spacing=tokens.SPACE_SM,
            ),
        ],
        spacing=8,
    )
    return ft.Container(
        content=ft.Column([header, skeleton], spacing=tokens.SPACE_SM),
        padding=tokens.SPACE_SM,
    )
