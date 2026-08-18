"""Header row, badges, retry controls, and suggestion chips for InsightCard."""

from __future__ import annotations

import flet as ft

from core import theme, tokens


def build_card_header(
    prompt: str,
    is_failed: bool,
    is_pinned: bool,
    pin_fn=None,
    on_delete=None,
    block: dict | None = None,
) -> ft.Row:
    """Build the top header row for an InsightCard with pin and delete buttons."""
    pin_btn = ft.IconButton(
        icon=ft.Icons.PUSH_PIN_ROUNDED if is_pinned else ft.Icons.PUSH_PIN_OUTLINED,
        icon_color=theme.ACCENT if is_pinned else ft.Colors.ON_SURFACE_VARIANT,
        icon_size=tokens.ICON_SM,
        tooltip="Unpin from Report" if is_pinned else "Pin to Report",
        on_click=lambda _: pin_fn(block) if pin_fn else None,
        style=ft.ButtonStyle(padding=tokens.SPACE_XXS),
    )

    delete_btn = ft.IconButton(
        icon=ft.Icons.CLOSE_ROUNDED,
        icon_color=ft.Colors.ON_SURFACE_VARIANT,
        icon_size=tokens.ICON_SM,
        tooltip="Remove Step",
        on_click=lambda _: on_delete() if on_delete else None,
        style=ft.ButtonStyle(padding=tokens.SPACE_XXS),
    )

    return ft.Row(
        controls=[
            ft.Row(
                [
                    ft.Icon(
                        ft.Icons.AUTO_AWESOME_ROUNDED
                        if not is_failed
                        else ft.Icons.ERROR_OUTLINE_ROUNDED,
                        size=tokens.ICON_SM,
                        color=theme.PRIMARY if not is_failed else theme.ERROR,
                    ),
                    ft.Text(
                        prompt,
                        size=tokens.FONT_SM,
                        weight=ft.FontWeight.W_600,
                        color=ft.Colors.ON_SURFACE,
                    ),
                ],
                spacing=tokens.SPACE_XS,
                expand=True,
            ),
            ft.Row([pin_btn, delete_btn], spacing=tokens.SPACE_NONE),
        ],
        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
    )


def build_executive_narration(narration: str, is_failed: bool) -> ft.Control | None:
    """Build the lightbulb insight callout box."""
    if not narration or is_failed:
        return None
    return ft.Container(
        content=ft.Row(
            [
                ft.Icon(
                    ft.Icons.LIGHTBULB_ROUNDED,
                    size=tokens.ICON_MD,
                    color=theme.ACCENT,
                ),
                ft.Text(
                    narration,
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
        bgcolor=ft.Colors.with_opacity(tokens.OPACITY_MUTED, theme.ACCENT),
        border_radius=tokens.RADIUS_MD,
        border=ft.Border.all(
            tokens.DIVIDER_THICKNESS,
            ft.Colors.with_opacity(tokens.OPACITY_BORDER, theme.ACCENT),
        ),
    )


def build_retry_button(
    is_failed: bool, prompt: str, on_retry_ai=None
) -> ft.Control | None:
    """Self-healing retry button shown when execution failed."""
    if not is_failed or not on_retry_ai:
        return None
    return ft.Row(
        [
            ft.TextButton(
                "Retry with AI Self-Healing",
                icon=ft.Icons.REFRESH_ROUNDED,
                style=ft.ButtonStyle(color=theme.WARNING),
                on_click=lambda _: on_retry_ai(prompt),
            )
        ],
        alignment=ft.MainAxisAlignment.END,
    )


def build_suggestion_chips(
    suggestions: list, on_suggestion_selected=None
) -> ft.Control | None:
    """Suggested next step chips attached to the card."""
    if not suggestions or not on_suggestion_selected:
        return None

    sugg_chips = []
    for s in suggestions[:3]:
        if isinstance(s, dict):
            label_txt = s.get("label") or s.get("prompt", "")
            icon_txt = s.get("icon", "✨")
            prompt_val = s.get("prompt") or label_txt
            disp = f"{icon_txt} {label_txt}".strip()
        else:
            prompt_val = str(s)
            disp = str(s)

        sugg_chips.append(
            ft.Chip(
                label=ft.Text(disp, size=tokens.FONT_XS),
                tooltip=prompt_val,
                on_click=lambda _, p=prompt_val: on_suggestion_selected(p),
            )
        )

    return ft.Column(
        [
            ft.Text(
                "Suggested next steps:",
                size=tokens.FONT_XS,
                weight=ft.FontWeight.W_600,
                color=ft.Colors.ON_SURFACE_VARIANT,
            ),
            ft.Row(sugg_chips, wrap=True, spacing=tokens.SPACE_XXS),
        ],
        spacing=tokens.SPACE_XXS,
    )
