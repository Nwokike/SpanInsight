"""Form card item component for Forms dashboard."""

from __future__ import annotations

from datetime import UTC, datetime

import flet as ft

from core import theme, tokens


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
                            size=tokens.FONT_MD,
                            max_lines=1,
                            overflow=ft.TextOverflow.ELLIPSIS,
                        ),
                        ft.Row(
                            [
                                ft.Container(
                                    content=ft.Text(
                                        status_text,
                                        size=tokens.FONT_XS,
                                        color=status_color,
                                        weight="bold",
                                    ),
                                    padding=ft.Padding(
                                        tokens.SPACE_SM_XS,
                                        tokens.SPACE_XXS,
                                        tokens.SPACE_SM_XS,
                                        tokens.SPACE_XXS,
                                    ),
                                    border_radius=tokens.RADIUS_XS,
                                    bgcolor=ft.Colors.with_opacity(
                                        tokens.OPACITY_LIGHT, status_color
                                    ),
                                ),
                                ft.Text(
                                    f"{form.get('response_count', 0)} responses",
                                    size=tokens.FONT_SM,
                                    color=ft.Colors.ON_SURFACE_VARIANT,
                                ),
                            ],
                            spacing=tokens.SPACE_SM,
                        ),
                    ],
                    spacing=tokens.SPACE_XS,
                    expand=True,
                ),
                ft.IconButton(
                    ft.Icons.ARROW_FORWARD_IOS_ROUNDED,
                    icon_size=tokens.ICON_SM,
                    on_click=lambda e: on_view(form),
                ),
            ]
        ),
        padding=tokens.BUTTON_PADDING_MD,
        border_radius=tokens.RADIUS_MD,
        bgcolor=theme.GLASS_BG,
        border=ft.Border.all(tokens.DIVIDER_THICKNESS, theme.GLASS_BORDER_COLOR),
        margin=ft.Margin(
            tokens.SPACE_XL, tokens.SPACE_NONE, tokens.SPACE_XL, tokens.SPACE_SM
        ),
        on_click=lambda e: on_view(form),
        ink=True,
    )
