"""Session card — reusable card showing session name, hardware, status.

Ported from CollabShell with SpanInsight theming.
"""

import flet as ft

from core import theme, tokens


def hardware_badge(accelerator: str, variant: str = "") -> ft.Container:
    """Colored hardware chip — CPU=gray, GPU=amber, TPU=blue."""
    label = "CPU" if accelerator == "NONE" else accelerator
    if variant == "TPU" or accelerator.upper() in ("V5E1", "V6E1"):
        color = theme.HARDWARE_TPU
    elif variant == "GPU" or accelerator not in ("NONE",):
        color = theme.HARDWARE_GPU
    else:
        color = theme.HARDWARE_CPU

    return ft.Container(
        content=ft.Text(
            label,
            size=tokens.FONT_XXS,
            weight=ft.FontWeight.W_700,
            color=ft.Colors.WHITE,
        ),
        bgcolor=color,
        border_radius=tokens.RADIUS_XS,
        padding=ft.Padding(
            tokens.SPACE_SM_XS,
            tokens.SPACE_XXS,
            tokens.SPACE_SM_XS,
            tokens.SPACE_XXS,
        ),
    )


def status_dot(is_running: bool = False) -> ft.Container:
    """Green dot for running, gray for idle."""
    return ft.Container(
        width=tokens.DOT_INDICATOR_WIDTH_INACTIVE,
        height=tokens.DOT_INDICATOR_HEIGHT,
        border_radius=tokens.RADIUS_XS,
        bgcolor=theme.SUCCESS if is_running else theme.HARDWARE_CPU,
    )


def build_session_card(session: dict, on_click=None) -> ft.Container:
    """Session card — name, hardware badge, status, last execution."""
    name = session.get("name", "?")
    accel_str = session.get("accelerator_label") or session.get("accelerator", "NONE")
    variant = session.get("variant", "DEFAULT")
    status = session.get("status", "IDLE")
    running = session.get("running")
    last_exec = session.get("last_execution")
    is_running = running is not None

    subtitle = ""
    if last_exec:
        subtitle = f"Last: {last_exec.get('file', '')} at {last_exec.get('time', '')}"
    elif status == "IDLE":
        subtitle = "Ready for analysis"

    return ft.Container(
        content=ft.Row(
            controls=[
                status_dot(is_running),
                ft.Column(
                    controls=[
                        ft.Row(
                            controls=[
                                ft.Text(
                                    name,
                                    size=tokens.FONT_LG,
                                    weight=ft.FontWeight.W_600,
                                ),
                                hardware_badge(accel_str, variant),
                            ],
                            spacing=tokens.SPACE_SM,
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                        ft.Text(
                            subtitle,
                            size=tokens.FONT_XS,
                            color=ft.Colors.ON_SURFACE_VARIANT,
                            max_lines=1,
                            overflow=ft.TextOverflow.ELLIPSIS,
                        ),
                    ],
                    spacing=tokens.SPACE_XXS,
                    expand=True,
                ),
                ft.Icon(
                    ft.Icons.CHEVRON_RIGHT_ROUNDED,
                    size=tokens.ICON_LG,
                    color=ft.Colors.ON_SURFACE_VARIANT,
                ),
            ],
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=tokens.SPACE_MD,
        ),
        padding=ft.Padding(
            tokens.SPACE_LG, tokens.SPACE_MD, tokens.SPACE_LG, tokens.SPACE_MD
        ),
        border_radius=tokens.RADIUS_MD,
        bgcolor=ft.Colors.with_opacity(tokens.OPACITY_FAINT, ft.Colors.ON_SURFACE),
        border=ft.Border.all(
            tokens.DIVIDER_THICKNESS,
            ft.Colors.with_opacity(tokens.OPACITY_LIGHT, ft.Colors.ON_SURFACE),
        ),
        margin=ft.Margin(
            tokens.SPACE_LG, tokens.SPACE_SM, tokens.SPACE_LG, tokens.SPACE_NONE
        ),
        on_click=on_click,
        ink=True,
    )
