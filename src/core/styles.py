"""Design system — reusable widget factories and style presets.

Use these instead of building raw containers with hardcoded values.
Mirrors the Fletbot styles.py pattern.
"""

from __future__ import annotations

import flet as ft

from core import theme, tokens


# ── Glass Card ────────────────────────────────────────────────────────
def glass_card(
    content: ft.Control,
    *,
    width: int | None = None,
    padding: int | ft.Padding = tokens.SPACE_XL,
    border_radius: int = tokens.RADIUS_XL,
    blur_sigma: int = 0,  # kept for signature compat, unused
) -> ft.Container:
    """Return a clean card container — no blur for mobile performance."""
    return ft.Container(
        content=content,
        width=width,
        padding=padding,
        border_radius=border_radius,
        bgcolor=theme.GLASS_BG,
        border=ft.Border.all(tokens.DIVIDER_THICKNESS, theme.GLASS_BORDER_COLOR),
        shadow=ft.BoxShadow(
            spread_radius=tokens.SPACE_NONE,
            blur_radius=tokens.SHADOW_BLUR,
            color=theme.SHADOW_DARK,
            offset=ft.Offset(tokens.SPACE_NONE, tokens.SHADOW_OFFSET_Y),
        ),
    )


# ── Solid Card (for light mode) ────────────────────────────────────
def solid_card(
    content: ft.Control,
    *,
    width: int | None = None,
    padding: int | ft.Padding = tokens.SPACE_XL,
    border_radius: int = tokens.RADIUS_XL,
    page: ft.Page | None = None,
) -> ft.Container:
    """Adaptive card — glass in dark mode, solid white in light."""
    is_dark = page and page.theme_mode == ft.ThemeMode.DARK
    if is_dark:
        return glass_card(
            content, width=width, padding=padding, border_radius=border_radius
        )
    return ft.Container(
        content=content,
        width=width,
        padding=padding,
        border_radius=border_radius,
        bgcolor=theme.LIGHT_SURFACE,
        border=ft.Border.all(tokens.DIVIDER_THICKNESS, theme.LIGHT_BORDER),
        shadow=ft.BoxShadow(
            spread_radius=tokens.SPACE_NONE,
            blur_radius=tokens.SHADOW_BLUR,
            color=ft.Colors.with_opacity(tokens.OPACITY_LIGHT, theme.SHADOW_DARK),
            offset=ft.Offset(tokens.SPACE_NONE, tokens.SHADOW_OFFSET_Y),
        ),
    )


# ── Gradient Background ─────────────────────────────────────────────
def gradient_bg(content: ft.Control, page: ft.Page | None = None) -> ft.Container:
    """Wrap *content* in the brand gradient background."""
    is_dark = not page or page.theme_mode != ft.ThemeMode.LIGHT
    return ft.Container(
        content=content,
        expand=True,
        gradient=theme.dark_gradient() if is_dark else theme.light_gradient(),
    )


# ── Section Header ──────────────────────────────────────────────────
def section_header(title: str) -> ft.Container:
    """Reusable section header for settings-style lists."""
    return ft.Container(
        content=ft.Text(
            title.upper(),
            size=tokens.FONT_XS,
            weight=ft.FontWeight.W_600,
            color=ft.Colors.PRIMARY,
            style=ft.TextStyle(letter_spacing=tokens.LETTER_SPACING_CAPS),
        ),
        padding=ft.Padding(
            left=tokens.SPACE_XS,
            top=tokens.SPACE_XL,
            bottom=tokens.SPACE_SM,
            right=tokens.SPACE_NONE,
        ),
    )


# ── Setting Tile ────────────────────────────────────────────────────
def setting_tile(
    icon: str,
    title: str,
    subtitle: str | ft.Control = "",
    trailing: ft.Control | None = None,
    on_click=None,
) -> ft.Container:
    """Reusable row for settings lists."""
    children: list[ft.Control] = [
        ft.Icon(icon, size=tokens.ICON_LG, color=ft.Colors.ON_SURFACE_VARIANT),
        ft.Column(
            controls=[
                ft.Text(title, size=tokens.FONT_MD, weight=ft.FontWeight.W_500),
                *(
                    [
                        subtitle
                        if isinstance(subtitle, ft.Control)
                        else ft.Text(
                            subtitle,
                            size=tokens.FONT_XS,
                            color=ft.Colors.ON_SURFACE_VARIANT,
                        )
                    ]
                    if subtitle
                    else []
                ),
            ],
            spacing=tokens.SPACE_XXS,
            expand=True,
        ),
    ]
    if trailing:
        children.append(trailing)

    return ft.Container(
        content=ft.Row(
            controls=children,
            spacing=tokens.SPACE_LG,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        padding=ft.Padding(
            left=tokens.SPACE_LG,
            right=tokens.SPACE_LG,
            top=tokens.BUTTON_PADDING_MD,
            bottom=tokens.BUTTON_PADDING_MD,
        ),
        border_radius=tokens.RADIUS_MD,
        ink=True,
        ink_color=ft.Colors.with_opacity(tokens.OPACITY_MUTED, theme.PRIMARY),
        on_click=on_click,
    )


# ── AppBar Builder ──────────────────────────────────────────────────
def standard_appbar(
    title: str,
    *,
    leading: ft.Control | None = None,
    actions: list[ft.Control] | None = None,
) -> ft.AppBar:
    """Build a consistent AppBar across all views."""
    return ft.AppBar(
        leading=leading,
        title=ft.Text(
            title,
            weight=ft.FontWeight.W_600,
            size=tokens.FONT_XL,
        ),
        center_title=False,
        bgcolor=ft.Colors.TRANSPARENT,
        actions=actions or [],
    )


# ── Dashed Border Container ────────────────────────────────────────
def dashed_border_container(
    content: ft.Control,
    *,
    width: int | None = None,
    height: int | None = None,
    border_color: str = theme.DARK_BORDER,
    border_radius: int = tokens.RADIUS_XL,
    on_click=None,
) -> ft.Container:
    """Container with a dashed-style border effect for upload areas."""
    return ft.Container(
        content=content,
        width=width,
        height=height,
        border_radius=border_radius,
        border=ft.Border.all(
            tokens.DIVIDER_THICKNESS_THICK,
            ft.Colors.with_opacity(tokens.OPACITY_MUTED_BORDER, border_color),
        ),
        bgcolor=ft.Colors.with_opacity(tokens.OPACITY_SUBTLE, ft.Colors.WHITE),
        alignment=ft.Alignment.CENTER,
        on_click=on_click,
        ink=True,
    )


# ── Primary Button Style ───────────────────────────────────────────
def primary_button_style() -> ft.ButtonStyle:
    """Rounded primary button style."""
    return ft.ButtonStyle(
        shape=ft.RoundedRectangleBorder(radius=tokens.RADIUS_MD),
        padding=ft.Padding(
            left=tokens.SPACE_XXL,
            right=tokens.SPACE_XXL,
            top=tokens.SPACE_MD,
            bottom=tokens.SPACE_MD,
        ),
    )


# ── Chip Button Style ──────────────────────────────────────────────
def chip_button_style() -> ft.ButtonStyle:
    """Style for suggestion chips."""
    return ft.ButtonStyle(
        shape=ft.RoundedRectangleBorder(radius=tokens.RADIUS_PILL),
        padding=ft.Padding(
            left=tokens.SPACE_LG,
            right=tokens.SPACE_LG,
            top=tokens.SPACE_SM,
            bottom=tokens.SPACE_SM,
        ),
    )


def build_banner_ad(page: ft.Page) -> ft.Container:
    """Build a styled banner ad container (mobile only)."""
    from core import utils

    is_mobile = page.platform in (ft.PagePlatform.ANDROID, ft.PagePlatform.IOS)
    if not is_mobile:
        return ft.Container()

    return ft.Container(
        content=ft.Column(
            [
                ft.Text(
                    "SPONSORED",
                    size=tokens.FONT_XXS,
                    weight=ft.FontWeight.W_700,
                    color=ft.Colors.ON_SURFACE_VARIANT,
                    style=ft.TextStyle(letter_spacing=tokens.SPACE_MICRO),
                ),
                utils.get_banner_ad(),
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=tokens.SPACE_XS,
        ),
        alignment=ft.Alignment.CENTER,
        padding=tokens.SPACE_SM,
        margin=ft.Margin(
            tokens.SPACE_NONE,
            tokens.SPACE_SM,
            tokens.SPACE_NONE,
            tokens.SPACE_SM,
        ),
    )
