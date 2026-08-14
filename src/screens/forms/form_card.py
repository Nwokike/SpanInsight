"""Form card item component for Forms dashboard."""

from __future__ import annotations

from datetime import UTC, datetime

import flet as ft

from core import theme


def render_form_card(form: dict, on_view) -> ft.Container:
    """Individual form item card with active/expired pill and response counter."""
    is_expired = False
    try:
        exp = datetime.fromisoformat(form["expires_at"])
        is_expired = exp < datetime.now(UTC)
    except Exception:
        pass
    status_color = theme.ERROR if is_expired else theme.SUCCESS
    status_text = "Expired" if is_expired else "Active"

    return ft.Container(
        content=ft.Row(
            [
                ft.Column(
                    [
                        ft.Text(
                            form["title"],
                            weight="bold",
                            size=14,
                            max_lines=1,
                            overflow="ellipsis",
                        ),
                        ft.Row(
                            [
                                ft.Container(
                                    content=ft.Text(
                                        status_text,
                                        size=9,
                                        color=status_color,
                                        weight="bold",
                                    ),
                                    padding=ft.Padding(6, 2, 6, 2),
                                    border_radius=4,
                                    bgcolor=ft.Colors.with_opacity(0.1, status_color),
                                ),
                                ft.Text(
                                    f"{form.get('response_count', 0)} responses",
                                    size=11,
                                    color=ft.Colors.ON_SURFACE_VARIANT,
                                ),
                            ],
                            spacing=8,
                        ),
                    ],
                    spacing=4,
                    expand=True,
                ),
                ft.IconButton(
                    ft.Icons.ARROW_FORWARD_IOS_ROUNDED,
                    icon_size=16,
                    on_click=lambda e: on_view(form),
                ),
            ]
        ),
        padding=14,
        border_radius=12,
        bgcolor=theme.GLASS_BG,
        border=ft.Border.all(1, theme.GLASS_BORDER_COLOR),
        margin=ft.Margin(20, 0, 20, 8),
        on_click=lambda e: on_view(form),
        ink=True,
    )
