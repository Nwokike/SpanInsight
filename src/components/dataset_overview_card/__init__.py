"""DatasetOverviewCard - SpanInsight's rich initial dataset overview component."""

from __future__ import annotations

import logging
from collections.abc import Callable

import flet as ft

from core import theme, tokens

from .column_chips import build_column_chips_section
from .summary_table import build_summary_table_section

logger = logging.getLogger("DatasetOverviewCard")


def build_dataset_overview_card(
    dataset_name: str,
    schema: dict,
    page: ft.Page,
    initial_description: str = "",
    suggestions: list[str] | None = None,
    on_suggestion_selected: Callable[[str], None] | None = None,
    on_view_raw_data: Callable[[], None] | None = None,
    on_inspect_schema: Callable[[], None] | None = None,
) -> ft.Container:
    """Build a rich glassmorphic Dataset Overview Card."""
    columns = schema.get("columns", [])
    dtypes = schema.get("dtypes", {})
    nulls = schema.get("nulls", {})
    shape = schema.get("shape", [0, 0])
    summary_stats = schema.get("summary", {})

    rows_count = shape[0] if len(shape) > 0 else 0
    cols_count = shape[1] if len(shape) > 1 else len(columns)

    controls: list[ft.Control] = []

    # 1. Header Row
    header_right_controls: list[ft.Control] = [
        ft.Container(
            content=ft.Text(
                f"{rows_count:,} rows × {cols_count} cols",
                size=tokens.FONT_XS,
                weight=ft.FontWeight.W_600,
                color=theme.PRIMARY,
            ),
            padding=ft.Padding(
                tokens.SPACE_SM, tokens.SPACE_XXS, tokens.SPACE_SM, tokens.SPACE_XXS
            ),
            bgcolor=ft.Colors.with_opacity(tokens.OPACITY_CONTAINER, theme.PRIMARY),
            border_radius=tokens.RADIUS_SM,
        )
    ]

    if on_view_raw_data:
        header_right_controls.append(
            ft.IconButton(
                icon=ft.Icons.TABLE_VIEW_ROUNDED,
                tooltip="Preview Raw Data",
                icon_size=tokens.ICON_MD,
                icon_color=theme.ACCENT,
                on_click=lambda _: on_view_raw_data(),
            )
        )

    if on_inspect_schema:
        header_right_controls.append(
            ft.IconButton(
                icon=ft.Icons.INFO_OUTLINE_ROUNDED,
                tooltip="Schema Details",
                icon_size=tokens.ICON_MD,
                icon_color=ft.Colors.ON_SURFACE_VARIANT,
                on_click=lambda _: on_inspect_schema(),
            )
        )

    header_row = ft.Row(
        controls=[
            ft.Row(
                controls=[
                    ft.Icon(
                        ft.Icons.DATASET_ROUNDED,
                        size=tokens.ICON_BASE,
                        color=theme.ACCENT,
                    ),
                    ft.Text(
                        dataset_name or "Active Dataset",
                        size=tokens.FONT_MD,
                        weight=ft.FontWeight.W_700,
                    ),
                ],
                spacing=tokens.SPACE_XS,
            ),
            ft.Row(
                controls=header_right_controls,
                spacing=tokens.SPACE_XS,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
        ],
        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
    )
    controls.append(header_row)

    # 2. AI Dataset Description Callout
    if initial_description and initial_description.strip():
        is_fallback = (
            "unavailable" in initial_description.lower()
            or "analyzing dataset" in initial_description.lower()
        )
        callout_color = ft.Colors.ON_SURFACE_VARIANT if is_fallback else theme.ACCENT
        callout_icon = (
            ft.Icons.INFO_OUTLINE_ROUNDED if is_fallback else ft.Icons.LIGHTBULB_ROUNDED
        )
        controls.append(
            ft.Container(
                content=ft.Row(
                    controls=[
                        ft.Icon(
                            callout_icon,
                            size=tokens.ICON_MD,
                            color=callout_color,
                        ),
                        ft.Text(
                            initial_description,
                            size=tokens.FONT_SM,
                            weight=ft.FontWeight.W_500,
                            color=ft.Colors.ON_SURFACE,
                            expand=True,
                        ),
                    ],
                    vertical_alignment=ft.CrossAxisAlignment.START,
                    spacing=tokens.SPACE_SM,
                ),
                padding=tokens.SPACE_MD,
                bgcolor=ft.Colors.with_opacity(tokens.OPACITY_MUTED, callout_color),
                border_radius=tokens.RADIUS_MD,
                border=ft.Border.all(
                    tokens.DIVIDER_THICKNESS,
                    ft.Colors.with_opacity(tokens.OPACITY_BORDER, callout_color),
                ),
            )
        )

    # 3. Column Chips
    chips_section = build_column_chips_section(columns, dtypes, nulls)
    if chips_section:
        controls.append(chips_section)

    # 4. Statistical Summary Table
    stats_section = build_summary_table_section(summary_stats)
    if stats_section:
        controls.append(stats_section)

    return ft.Container(
        content=ft.Column(controls=controls, spacing=tokens.SPACE_SM),
        padding=tokens.SPACE_MD,
        border_radius=tokens.RADIUS_LG,
        bgcolor=theme.GLASS_BG,
        border=ft.Border.all(tokens.DIVIDER_THICKNESS, theme.GLASS_BORDER_COLOR),
        margin=ft.Margin(
            tokens.SPACE_NONE, tokens.SPACE_NONE, tokens.SPACE_NONE, tokens.SPACE_SM
        ),
    )


__all__ = ["build_dataset_overview_card"]
