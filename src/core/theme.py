"""Design system — colour palette, gradients, and Material 3 theme.

Every colour used anywhere in Spaninsight lives here.
Palette derived from brand logo: Teal (primary) + Orange (accent/CTA).
"""

from __future__ import annotations

import flet as ft

# ── Brand Palette ───────────────────────────────────────────────────
PRIMARY = "#00897B"  # Teal 600 — brand primary
PRIMARY_DARK = "#00796B"  # Teal 700 — pressed state
PRIMARY_LIGHT = "#4DB6AC"  # Teal 300 — hover / light variant
ACCENT = "#F4831F"  # Warm Orange — CTA / secondary
ACCENT_DIM = "#E07316"  # Deep Orange — subdued accent

SUCCESS = "#2E7D32"  # Green 800
WARNING = "#F9A825"  # Amber 800
ERROR = "#D32F2F"  # Red 700

# ── Dark Mode Surfaces (M3 Surface Container hierarchy) ────────────
DARK_BG_1 = "#0F1114"  # Background
DARK_BG_2 = "#121518"  # Surface
DARK_SURFACE = "#1A1D22"  # Surface Container Low — cards
DARK_SURFACE_2 = "#252A30"  # Surface Container High — dialogs
DARK_BORDER = "#2E3339"  # Outline / dividers
DARK_TEXT = "#ECEFF1"  # On Surface
DARK_TEXT_DIM = "#90A4AE"  # On Surface Variant

LIGHT_BG = "#FAFAFA"
LIGHT_SURFACE = "#FFFFFF"
LIGHT_SURFACE_2 = "#F5F5F5"
LIGHT_BORDER = "#E0E0E0"
LIGHT_TEXT = "#1A1A2E"
LIGHT_TEXT_DIM = "#757575"

# ── Surface Cards (solid, crisp Material 3 containers) ──────────────
GLASS_BG_OPACITY = 0.06
GLASS_BORDER_OPACITY = 0.12
GLASS_BG = ft.Colors.SURFACE_CONTAINER_LOW
GLASS_BORDER_COLOR = ft.Colors.OUTLINE_VARIANT

LIGHT_GLASS_BG = ft.Colors.SURFACE_CONTAINER_LOW
LIGHT_GLASS_BORDER = ft.Colors.OUTLINE_VARIANT

# ── Shadows ─────────────────────────────────────────────────────────
SHADOW_PRIMARY = ft.Colors.with_opacity(0.20, PRIMARY)
SHADOW_DARK = ft.Colors.with_opacity(0.12, "#000000")

# ── Semantic additions ──────────────────────────────────────────────
INFO = "#42A5F5"  # Blue — info badges, Colab status

# ── Terminal & Output ───────────────────────────────────────────────
TERMINAL_BG = "#0D0D1A"
LOG_TERMINAL_BG = "#0D0D0D"
TERMINAL_CONSOLE_BG = "#0D0D0D"
TERMINAL_GREEN = "#A6E22E"
TERMINAL_HEADER = "#1A1A2E"
TERMINAL_TEXT_MUTED = "#E0E0E0"
TERMINAL_DOT_RED = "#FF5F56"
TERMINAL_DOT_YELLOW = "#FFBD2E"
TERMINAL_DOT_GREEN = "#28C840"

# ── Chart Color Palette ─────────────────────────────────────────────
CHART_PALETTE = [
    "#7C4DFF",
    "#00BFA5",
    "#FF7043",
    "#5C9DED",
    "#EC407A",
    "#9CCC65",
]

# ── Standard 16-color ANSI Palette ──────────────────────────────────
ANSI_COLORS = {
    0: "#000000",
    1: "#CC0000",
    2: "#4E9A06",
    3: "#C4A000",
    4: "#3465A4",
    5: "#75507B",
    6: "#06989A",
    7: "#D3D7CF",
    8: "#555753",
    9: "#EF2929",
    10: "#8AE234",
    11: "#FCE94F",
    12: "#729FCF",
    13: "#AD7FA8",
    14: "#34E2E2",
    15: "#EEEEEC",
}

# ── Hardware Badge Colours ──────────────────────────────────────────
BADGE_CPU = "#78909C"  # Blue-gray for CPU
BADGE_GPU = "#E58514"  # Orange for GPU
BADGE_TPU = "#42A5F5"  # Blue for TPU
BADGE_FREE = "#4CAF50"  # Green — free tier
BADGE_PAID = "#AB47BC"  # Purple — paid tier
HARDWARE_CPU = BADGE_CPU
HARDWARE_GPU = BADGE_GPU
HARDWARE_TPU = BADGE_TPU
CREDIT_HIGH = PRIMARY  # > 20 credits — teal (brand)
CREDIT_MEDIUM = WARNING  # 5–20 credits
CREDIT_LOW = ERROR  # < 5 credits


# ── Gradient Builders ───────────────────────────────────────────────
def dark_gradient() -> ft.LinearGradient:
    """Subtle dark gradient — nearly flat for performance."""
    return ft.LinearGradient(
        begin=ft.Alignment.TOP_CENTER,
        end=ft.Alignment.BOTTOM_CENTER,
        colors=[DARK_BG_1, DARK_BG_2],
    )


def light_gradient() -> ft.LinearGradient:
    """Subtle warm gradient for light mode."""
    return ft.LinearGradient(
        begin=ft.Alignment.TOP_CENTER,
        end=ft.Alignment.BOTTOM_CENTER,
        colors=["#F5F5F5", LIGHT_BG],
    )


def accent_gradient() -> ft.LinearGradient:
    """Teal-to-orange gradient for primary action highlights."""
    return ft.LinearGradient(
        begin=ft.Alignment.BOTTOM_LEFT,
        end=ft.Alignment.TOP_RIGHT,
        colors=[PRIMARY, PRIMARY_LIGHT, ACCENT],
    )


def adaptive_glass_bg(page: ft.Page | None = None):
    """Return card background color appropriate for current theme."""
    if page and page.theme_mode == ft.ThemeMode.LIGHT:
        return LIGHT_GLASS_BG
    return GLASS_BG


def adaptive_glass_border(page: ft.Page | None = None):
    """Return card border color appropriate for current theme."""
    if page and page.theme_mode == ft.ThemeMode.LIGHT:
        return LIGHT_GLASS_BORDER
    return GLASS_BORDER_COLOR


class AppTheme:
    """Build Material 3 themes for Spaninsight — teal/orange."""

    @staticmethod
    def get_dark_theme() -> ft.Theme:
        return ft.Theme(
            color_scheme=ft.ColorScheme(
                primary=PRIMARY,
                on_primary=ft.Colors.WHITE,
                primary_container="#004D40",
                on_primary_container="#A7F3D0",
                secondary=ACCENT,
                on_secondary=ft.Colors.WHITE,
                secondary_container="#7B3F00",
                on_secondary_container="#FFE0B2",
                tertiary="#F9A825",
                on_tertiary=ft.Colors.BLACK,
                surface=DARK_BG_2,
                on_surface=DARK_TEXT,
                on_surface_variant=DARK_TEXT_DIM,
                surface_container_lowest=DARK_BG_1,
                surface_container_low=DARK_SURFACE,
                surface_container=DARK_SURFACE,
                surface_container_high=DARK_SURFACE_2,
                surface_container_highest="#2C3138",
                error=ERROR,
                on_error=ft.Colors.WHITE,
                outline=DARK_BORDER,
                outline_variant="#1E2228",
            ),
            navigation_bar_theme=ft.NavigationBarTheme(
                indicator_color=ft.Colors.with_opacity(0.16, PRIMARY),
                label_text_style=ft.TextStyle(size=10, weight=ft.FontWeight.W_500),
            ),
            visual_density=ft.VisualDensity.COMFORTABLE,
        )

    @staticmethod
    def get_light_theme() -> ft.Theme:
        return ft.Theme(
            color_scheme=ft.ColorScheme(
                primary=PRIMARY,
                on_primary=ft.Colors.WHITE,
                primary_container="#B2DFDB",
                on_primary_container="#00251A",
                secondary=ACCENT,
                on_secondary=ft.Colors.WHITE,
                secondary_container="#FFE0B2",
                on_secondary_container="#4E2600",
                tertiary="#F9A825",
                on_tertiary=ft.Colors.BLACK,
                surface=LIGHT_BG,
                on_surface=LIGHT_TEXT,
                on_surface_variant=LIGHT_TEXT_DIM,
                surface_container_lowest="#FFFFFF",
                surface_container_low=LIGHT_SURFACE,
                surface_container=LIGHT_SURFACE,
                surface_container_high=LIGHT_SURFACE_2,
                surface_container_highest="#EEEEEE",
                error=ERROR,
                on_error=ft.Colors.WHITE,
                outline=LIGHT_BORDER,
                outline_variant="#F5F5F5",
            ),
            navigation_bar_theme=ft.NavigationBarTheme(
                indicator_color=ft.Colors.with_opacity(0.16, PRIMARY),
                label_text_style=ft.TextStyle(size=10, weight=ft.FontWeight.W_500),
            ),
            visual_density=ft.VisualDensity.COMFORTABLE,
        )
