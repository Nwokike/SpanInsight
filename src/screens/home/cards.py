"""Card widgets for HomeScreen: quick actions, feature cards, and step rows."""

from __future__ import annotations

import flet as ft

from core import theme, tokens


def action_card(
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


def feature_card(icon: str, title: str, desc: str, color: str) -> ft.Container:
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


def step_row(number: str, title: str, desc: str) -> ft.Row:
    """Numbered step row for 'How It Works' guide."""
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


def project_card(project: dict, on_open, on_delete=None) -> ft.Container:
    """Card item displaying project metadata, dataset name, hardware, and cell count."""
    import datetime

    updated_at = project.get("updated_at", 0)
    try:
        dt = datetime.datetime.fromtimestamp(updated_at, tz=datetime.UTC)
        time_str = dt.strftime("%b %d")
    except Exception:
        time_str = ""

    return ft.Container(
        content=ft.Row(
            controls=[
                ft.Container(
                    content=ft.Icon(
                        ft.Icons.ANALYTICS_ROUNDED, size=24, color=theme.PRIMARY
                    ),
                    width=44,
                    height=44,
                    border_radius=tokens.RADIUS_MD,
                    bgcolor=ft.Colors.with_opacity(0.1, theme.PRIMARY),
                    alignment=ft.Alignment.CENTER,
                ),
                ft.Column(
                    controls=[
                        ft.Text(
                            project.get("name", "Untitled Project"),
                            size=tokens.FONT_SM,
                            weight=ft.FontWeight.W_600,
                            max_lines=1,
                            overflow="ellipsis",
                        ),
                        ft.Text(
                            f"{project.get('primary_dataset') or 'Empty notebook'} · {project.get('cell_count', 0)} cells · {time_str}",
                            size=tokens.FONT_XS,
                            color=ft.Colors.ON_SURFACE_VARIANT,
                            max_lines=1,
                            overflow="ellipsis",
                        ),
                    ],
                    spacing=2,
                    expand=True,
                ),
                ft.Container(
                    content=ft.Text(
                        project.get("hardware", "CPU"),
                        size=tokens.FONT_XXS,
                        weight=ft.FontWeight.W_600,
                        color=theme.PRIMARY,
                    ),
                    padding=ft.Padding(6, 2, 6, 2),
                    border_radius=tokens.RADIUS_SM,
                    bgcolor=ft.Colors.with_opacity(0.1, theme.PRIMARY),
                ),
                ft.Icon(
                    ft.Icons.CHEVRON_RIGHT_ROUNDED,
                    size=20,
                    color=ft.Colors.ON_SURFACE_VARIANT,
                ),
            ],
            spacing=tokens.SPACE_MD,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        padding=tokens.SPACE_MD,
        border_radius=tokens.RADIUS_LG,
        bgcolor=theme.GLASS_BG,
        border=ft.Border.all(1, theme.GLASS_BORDER_COLOR),
        on_click=lambda e: on_open(project),
        ink=True,
    )


def build_recent_projects_section(
    projects: list[dict], on_open, on_create_new
) -> ft.Container:
    """Renders recent projects list on the Home screen."""
    controls = [
        ft.Row(
            controls=[
                ft.Text(
                    "Recent Projects", size=tokens.FONT_MD, weight=ft.FontWeight.W_600
                ),
                ft.Container(expand=True),
                ft.TextButton(
                    "+ New Project",
                    style=ft.ButtonStyle(color=theme.PRIMARY),
                    on_click=on_create_new,
                ),
            ],
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        ft.Container(height=tokens.SPACE_SM),
    ]

    if not projects:
        controls.append(
            ft.Container(
                content=ft.Text(
                    "No saved projects yet. Start analyzing a dataset or create a new project above.",
                    size=tokens.FONT_XS,
                    color=ft.Colors.ON_SURFACE_VARIANT,
                ),
                padding=ft.Padding(0, tokens.SPACE_XS, 0, tokens.SPACE_SM),
            )
        )
    else:
        for p in projects[:4]:  # Show top 4 recent
            controls.append(project_card(p, on_open))
            controls.append(ft.Container(height=tokens.SPACE_XS))

    return ft.Container(
        content=ft.Column(controls=controls, spacing=0),
        padding=ft.Padding(tokens.SPACE_LG, 0, tokens.SPACE_LG, tokens.SPACE_MD),
    )
