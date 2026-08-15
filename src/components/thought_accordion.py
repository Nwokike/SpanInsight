"""ThoughtAccordion — displays collapsible chain-of-thought reasoning for modern AI models."""

from __future__ import annotations

import flet as ft

from core import theme, tokens


def build_thought_accordion(block: dict, on_change=None) -> ft.Control | None:
    """Builds a collapsible accordion showing the model's internal reasoning process."""
    thought = block.get("thought", "")
    if not thought or not str(thought).strip():
        return None

    duration = block.get("thought_duration", 0.0)
    model = block.get("model", "")
    show_thought = block.get("_show_thought", False)

    duration_str = f"{duration:.1f}s" if duration > 0 else ""
    header_title = (
        f"Thought for {duration_str}" if duration_str else "Reasoning Process"
    )

    def _toggle(_):
        block["_show_thought"] = not show_thought
        if on_change:
            on_change()

    toggle_btn = ft.Container(
        content=ft.Row(
            controls=[
                ft.Row(
                    [
                        ft.Icon(
                            ft.Icons.PSYCHOLOGY_ROUNDED,
                            size=14,
                            color=theme.PRIMARY,
                        ),
                        ft.Text(
                            header_title,
                            size=tokens.FONT_XS,
                            weight=ft.FontWeight.W_600,
                            color=theme.PRIMARY,
                        ),
                        ft.Text(
                            f"· {model}" if model and model != "unknown" else "",
                            size=tokens.FONT_XXS,
                            color=ft.Colors.ON_SURFACE_VARIANT,
                        ),
                    ],
                    spacing=tokens.SPACE_XXS,
                ),
                ft.Icon(
                    ft.Icons.KEYBOARD_ARROW_UP_ROUNDED
                    if show_thought
                    else ft.Icons.KEYBOARD_ARROW_DOWN_ROUNDED,
                    size=16,
                    color=ft.Colors.ON_SURFACE_VARIANT,
                ),
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        ),
        padding=ft.Padding(
            tokens.SPACE_SM, tokens.SPACE_XXS, tokens.SPACE_SM, tokens.SPACE_XXS
        ),
        bgcolor=ft.Colors.with_opacity(0.06, theme.PRIMARY),
        border_radius=tokens.RADIUS_SM,
        on_click=_toggle,
        ink=True,
    )

    if not show_thought:
        return toggle_btn

    body = ft.Container(
        content=ft.Column(
            [
                toggle_btn,
                ft.Container(
                    content=ft.Markdown(
                        thought.strip(),
                        selectable=True,
                        extension_set=ft.MarkdownExtensionSet.GITHUB_FLAVORED,
                    ),
                    padding=ft.Padding(
                        tokens.SPACE_SM,
                        tokens.SPACE_XS,
                        tokens.SPACE_SM,
                        tokens.SPACE_XS,
                    ),
                    bgcolor=ft.Colors.with_opacity(0.03, ft.Colors.ON_SURFACE),
                    border_radius=tokens.RADIUS_SM,
                    border=ft.Border.all(
                        1, ft.Colors.with_opacity(0.08, ft.Colors.ON_SURFACE)
                    ),
                ),
            ],
            spacing=tokens.SPACE_XXS,
        )
    )
    return body
