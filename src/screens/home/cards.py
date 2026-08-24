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
                    width=tokens.ICON_HERO,
                    height=tokens.ICON_HERO,
                    border_radius=tokens.RADIUS_MD,
                    bgcolor=ft.Colors.with_opacity(tokens.OPACITY_LIGHT, color),
                    alignment=ft.Alignment.CENTER,
                ),
                ft.Text(title, size=tokens.FONT_SM, weight=ft.FontWeight.W_600),
                ft.Text(
                    subtitle,
                    size=tokens.FONT_XXS,
                    color=ft.Colors.ON_SURFACE_VARIANT,
                ),
            ],
            spacing=tokens.SPACE_XS,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        expand=True,
        padding=tokens.SPACE_MD,
        border_radius=tokens.RADIUS_LG,
        bgcolor=theme.GLASS_BG,
        border=ft.Border.all(tokens.DIVIDER_THICKNESS, theme.GLASS_BORDER_COLOR),
        on_click=on_click,
        ink=True,
    )


def feature_card(icon: str, title: str, desc: str, color: str) -> ft.Container:
    """Marketing feature card."""
    return ft.Container(
        content=ft.Row(
            controls=[
                ft.Container(
                    content=ft.Icon(icon, size=tokens.ICON_MD_LG, color=color),
                    width=tokens.ICON_CONTAINER_SIZE,
                    height=tokens.ICON_CONTAINER_SIZE,
                    border_radius=tokens.RADIUS_MD_SM,
                    bgcolor=ft.Colors.with_opacity(tokens.OPACITY_LIGHT, color),
                    alignment=ft.Alignment.CENTER,
                ),
                ft.Column(
                    controls=[
                        ft.Text(
                            title,
                            size=tokens.FONT_SM,
                            weight=ft.FontWeight.W_600,
                        ),
                        ft.Text(
                            desc,
                            size=tokens.FONT_XS,
                            color=ft.Colors.ON_SURFACE_VARIANT,
                            max_lines=3,
                            overflow=ft.TextOverflow.ELLIPSIS,
                        ),
                    ],
                    spacing=tokens.SPACE_XXS,
                    expand=True,
                ),
            ],
            spacing=tokens.SPACE_MD,
            vertical_alignment=ft.CrossAxisAlignment.START,
        ),
        padding=tokens.SPACE_MD,
        border_radius=tokens.RADIUS_MD_SM,
        bgcolor=theme.GLASS_BG,
        border=ft.Border.all(tokens.DIVIDER_THICKNESS, theme.GLASS_BORDER_COLOR),
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
                width=tokens.ICON_CONTAINER_SM,
                height=tokens.ICON_CONTAINER_SM,
                border_radius=tokens.RADIUS_PILL,
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
    """Renders a single project summary card."""
    import datetime

    updated_at = project.get("updated_at", 0)
    try:
        dt = datetime.datetime.fromtimestamp(updated_at, tz=datetime.UTC)
        time_str = dt.strftime("%b %d")
    except Exception:
        time_str = ""

    card_controls = [
        ft.Container(
            content=ft.Icon(
                ft.Icons.ANALYTICS_ROUNDED,
                size=tokens.ICON_LG,
                color=theme.PRIMARY,
            ),
            width=tokens.BUTTON_HEIGHT_LG,
            height=tokens.BUTTON_HEIGHT_LG,
            border_radius=tokens.RADIUS_MD,
            bgcolor=ft.Colors.with_opacity(tokens.OPACITY_LIGHT, theme.PRIMARY),
            alignment=ft.Alignment.CENTER,
        ),
        ft.Column(
            controls=[
                ft.Text(
                    project.get("name", "Untitled Project"),
                    size=tokens.FONT_SM,
                    weight=ft.FontWeight.W_600,
                    max_lines=1,
                    overflow=ft.TextOverflow.ELLIPSIS,
                ),
                ft.Text(
                    f"{project.get('primary_dataset') or 'Empty notebook'} · {project.get('cell_count', 0)} cells · {time_str}",
                    size=tokens.FONT_XS,
                    color=ft.Colors.ON_SURFACE_VARIANT,
                    max_lines=1,
                    overflow=ft.TextOverflow.ELLIPSIS,
                ),
            ],
            spacing=tokens.SPACE_XXS,
            expand=True,
        ),
        ft.Container(
            content=ft.Text(
                project.get("hardware", "CPU"),
                size=tokens.FONT_XXS,
                weight=ft.FontWeight.W_600,
                color=theme.PRIMARY,
            ),
            padding=ft.Padding(
                tokens.SPACE_SM_XS,
                tokens.SPACE_XXS,
                tokens.SPACE_SM_XS,
                tokens.SPACE_XXS,
            ),
            border_radius=tokens.RADIUS_SM,
            bgcolor=ft.Colors.with_opacity(tokens.OPACITY_LIGHT, theme.PRIMARY),
        ),
    ]

    if on_delete:
        card_controls.append(
            ft.IconButton(
                icon=ft.Icons.DELETE_OUTLINE_ROUNDED,
                icon_size=tokens.ICON_SM_MD,
                icon_color=theme.ERROR,
                tooltip="Delete Project",
                on_click=lambda e: on_delete(project),
                style=ft.ButtonStyle(padding=tokens.SPACE_XXS),
            )
        )
    else:
        card_controls.append(
            ft.Icon(
                ft.Icons.CHEVRON_RIGHT_ROUNDED,
                size=tokens.ICON_MD,
                color=ft.Colors.ON_SURFACE_VARIANT,
            )
        )

    return ft.Container(
        content=ft.Row(
            controls=card_controls,
            spacing=tokens.SPACE_MD,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        padding=tokens.SPACE_MD,
        border_radius=tokens.RADIUS_LG,
        bgcolor=theme.GLASS_BG,
        border=ft.Border.all(tokens.DIVIDER_THICKNESS, theme.GLASS_BORDER_COLOR),
        on_click=lambda e: on_open(project),
        ink=True,
    )


def build_recent_projects_section(
    projects: list[dict], on_open, on_create_new, on_delete=None, on_view_all=None
) -> ft.Container:
    """Renders recent projects list (up to 5 items) on the Home screen."""
    controls = [
        ft.Row(
            controls=[
                ft.Text(
                    "Recent Projects",
                    size=tokens.FONT_MD,
                    weight=ft.FontWeight.W_600,
                ),
                ft.Container(expand=True),
                ft.Row(
                    [
                        ft.TextButton(
                            "View All",
                            style=ft.ButtonStyle(color=ft.Colors.ON_SURFACE_VARIANT),
                            on_click=on_view_all,
                        )
                        if on_view_all and len(projects) > 0
                        else ft.Container(),
                        ft.TextButton(
                            "+ New Project",
                            style=ft.ButtonStyle(color=theme.PRIMARY),
                            on_click=on_create_new,
                        ),
                    ],
                    spacing=tokens.SPACE_XXS,
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
                padding=ft.Padding(
                    tokens.SPACE_NONE,
                    tokens.SPACE_XS,
                    tokens.SPACE_NONE,
                    tokens.SPACE_SM,
                ),
            )
        )
    else:
        for p in projects[:5]:  # Show top 5 recent
            controls.append(project_card(p, on_open, on_delete=on_delete))
            controls.append(ft.Container(height=tokens.SPACE_XS))

    return ft.Container(
        content=ft.Column(controls=controls, spacing=tokens.SPACE_NONE),
        padding=ft.Padding(
            tokens.SPACE_LG,
            tokens.SPACE_NONE,
            tokens.SPACE_LG,
            tokens.SPACE_MD,
        ),
    )


def build_findings_section(
    project_name: str, findings: list[dict]
) -> ft.Container | None:
    """'What we know' — verified insights the project has accumulated."""
    items = [f for f in (findings or []) if f.get("text")]
    if not items:
        return None

    rows = []
    for f in items[:5]:
        nums = f.get("key_numbers") or []
        meta_bits = []
        if nums:
            meta_bits.append(" · ".join(str(n) for n in nums[:2]))
        meta_line = "  ".join(meta_bits)
        rows.append(
            ft.Container(
                content=ft.Row(
                    [
                        ft.Icon(
                            ft.Icons.VERIFIED_ROUNDED,
                            size=tokens.ICON_XS,
                            color=theme.SUCCESS,
                        ),
                        ft.Column(
                            [
                                ft.Text(
                                    str(f.get("text")),
                                    size=tokens.FONT_SM,
                                    max_lines=2,
                                    overflow=ft.TextOverflow.ELLIPSIS,
                                ),
                                ft.Text(
                                    meta_line or str(f.get("question", ""))[:80],
                                    size=tokens.FONT_XXS,
                                    color=ft.Colors.ON_SURFACE_VARIANT,
                                    max_lines=1,
                                    overflow=ft.TextOverflow.ELLIPSIS,
                                )
                                if (meta_line or f.get("question"))
                                else ft.Container(height=0),
                            ],
                            spacing=tokens.SPACE_MICRO,
                            expand=True,
                        ),
                    ],
                    spacing=tokens.SPACE_SM,
                    vertical_alignment=ft.CrossAxisAlignment.START,
                ),
                padding=tokens.SPACE_SM,
                border_radius=tokens.RADIUS_MD,
                bgcolor=ft.Colors.with_opacity(tokens.OPACITY_FAINT, theme.SUCCESS),
            )
        )

    header = ft.Row(
        [
            ft.Icon(
                ft.Icons.PSYCHOLOGY_ROUNDED, size=tokens.ICON_SM, color=theme.ACCENT
            ),
            ft.Text(
                f"What we know · {project_name}",
                size=tokens.FONT_BODY,
                weight=ft.FontWeight.W_700,
                expand=True,
            ),
            ft.Text(
                f"{len(items)} verified",
                size=tokens.FONT_XXS,
                color=ft.Colors.ON_SURFACE_VARIANT,
            ),
        ],
        spacing=tokens.SPACE_XS,
    )

    return ft.Container(
        content=ft.Column(
            [header, ft.Column(rows, spacing=tokens.SPACE_XS)],
            spacing=tokens.SPACE_SM,
        ),
        margin=ft.Margin(
            tokens.SPACE_XL, tokens.SPACE_XS, tokens.SPACE_XL, tokens.SPACE_NONE
        ),
        padding=tokens.SPACE_MD,
        border_radius=tokens.RADIUS_LG,
        bgcolor=theme.GLASS_BG,
        border=ft.Border.all(tokens.DIVIDER_THICKNESS, theme.GLASS_BORDER_COLOR),
    )
