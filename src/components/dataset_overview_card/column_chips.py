"""Column chips and null indicators for DatasetOverviewCard."""

from __future__ import annotations

import flet as ft

from core import theme, tokens


def build_column_chips_section(
    columns: list, dtypes: dict, nulls: dict
) -> ft.Control | None:
    """Build the list of column type chips with colored null badges."""
    if not columns:
        return None

    col_chips = []
    for col in columns[:30]:
        col_str = str(col)
        dtype = dtypes.get(col_str, "object")
        null_ct = nulls.get(col_str, 0)
        null_badge_color = theme.ERROR if null_ct > 0 else theme.SUCCESS
        null_badge_txt = f"{null_ct:,} null" if null_ct > 0 else "0 null"

        col_chips.append(
            ft.Container(
                content=ft.Column(
                    controls=[
                        ft.Text(
                            col_str[:18],
                            size=tokens.FONT_XS,
                            weight=ft.FontWeight.W_600,
                            max_lines=1,
                            overflow=ft.TextOverflow.ELLIPSIS,
                        ),
                        ft.Row(
                            controls=[
                                ft.Text(
                                    str(dtype),
                                    size=tokens.FONT_XS,
                                    color=ft.Colors.ON_SURFACE_VARIANT,
                                ),
                                ft.Container(
                                    content=ft.Text(
                                        null_badge_txt,
                                        size=tokens.FONT_XXS,
                                        weight=ft.FontWeight.W_700,
                                        color=null_badge_color,
                                    ),
                                    padding=ft.Padding(
                                        tokens.SPACE_TINY,
                                        tokens.SPACE_NONE,
                                        tokens.SPACE_TINY,
                                        tokens.SPACE_NONE,
                                    ),
                                    bgcolor=ft.Colors.with_opacity(
                                        tokens.OPACITY_CONTAINER, null_badge_color
                                    ),
                                    border_radius=tokens.RADIUS_SM,
                                ),
                            ],
                            spacing=tokens.SPACE_XS,
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                    ],
                    spacing=tokens.SPACE_XXS,
                    horizontal_alignment=ft.CrossAxisAlignment.START,
                ),
                padding=ft.Padding(
                    tokens.SPACE_XS,
                    tokens.SPACE_XXS,
                    tokens.SPACE_XS,
                    tokens.SPACE_XXS,
                ),
                border_radius=tokens.RADIUS_SM,
                bgcolor=ft.Colors.with_opacity(
                    tokens.OPACITY_FAINT, ft.Colors.ON_SURFACE
                ),
                border=ft.Border.all(
                    tokens.DIVIDER_THICKNESS,
                    ft.Colors.with_opacity(tokens.OPACITY_LIGHT, ft.Colors.ON_SURFACE),
                ),
            )
        )

    return ft.Column(
        controls=[
            ft.Row(
                controls=[
                    ft.Icon(
                        ft.Icons.VIEW_COLUMN_ROUNDED,
                        size=tokens.ICON_XS,
                        color=theme.ACCENT,
                    ),
                    ft.Text(
                        f"Columns ({len(columns)})",
                        size=tokens.FONT_XS,
                        weight=ft.FontWeight.W_600,
                    ),
                ],
                spacing=tokens.SPACE_XXS,
            ),
            ft.Row(controls=col_chips, wrap=True, spacing=tokens.SPACE_XXS),
        ],
        spacing=tokens.SPACE_XS,
    )
