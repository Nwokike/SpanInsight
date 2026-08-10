"""Suggestion chips — compact AI analysis action pills.

Renders as tiny, tappable pills in a wrapping row. NOT large cards.
The AI generates these dynamically after analyzing the dataset schema.
When credits are depleted, chips link directly to the credits dialog.
"""

from __future__ import annotations

import flet as ft

from components.credit_badge import show_credits_dialog
from core import theme, tokens
from core.state import state


def build_suggestion_chips(
    suggestions: list[dict],
    on_select: callable,
    is_loading: bool = False,
    page: ft.Page | None = None,
    credit_service=None,
) -> ft.Column:
    """Build a wrap of tiny suggestion pills.

    Args:
        suggestions: List of dicts with "label", "icon", "prompt" keys.
        on_select: Callback(prompt: str) when a chip is tapped.
        is_loading: Show disabled state during AI call.
        page: Flet page instance (required for credits dialog fallback).
        credit_service: CreditService instance (required for credits dialog fallback).
    """
    if not suggestions:
        return ft.Column()

    no_credits = state.credits_remaining <= 0

    pills = []
    for s in suggestions:
        label = s.get("label", "Analyze")
        icon_text = s.get("icon", "📊")
        prompt = s.get("prompt", "")

        def _make_handler(p, nc=no_credits):
            if nc and page and credit_service:
                return lambda e: show_credits_dialog(page, credit_service)
            return lambda e, p=p: on_select(p) if not is_loading else None

        pill = ft.Container(
            content=ft.Row(
                controls=[
                    ft.Text(icon_text, size=12),
                    ft.Text(
                        label,
                        size=11,
                        weight=ft.FontWeight.W_500,
                        max_lines=1,
                        overflow=ft.TextOverflow.ELLIPSIS,
                    ),
                ],
                spacing=4,
                tight=True,
            ),
            padding=ft.Padding(left=10, right=10, top=6, bottom=6),
            border_radius=20,
            bgcolor=ft.Colors.with_opacity(0.06, theme.PRIMARY),
            border=ft.Border.all(1, ft.Colors.with_opacity(0.15, theme.PRIMARY)),
            on_click=_make_handler(prompt),
            ink=True,
            disabled=is_loading and not no_credits,
        )
        pills.append(pill)

    return ft.Column(
        controls=[
            ft.Text(
                "✨ Suggestions",
                size=tokens.FONT_XS,
                weight=ft.FontWeight.W_600,
                color=ft.Colors.ON_SURFACE_VARIANT,
            ),
            ft.Row(
                controls=pills,
                wrap=True,
                spacing=6,
                run_spacing=6,
            ),
        ],
        spacing=6,
    )
