"""ThoughtAccordion - displays collapsible chain-of-thought reasoning for modern AI models."""

from __future__ import annotations

import logging

import flet as ft

from core import theme, tokens

logger = logging.getLogger("ThoughtAccordion")


def build_thought_accordion(block: dict, on_change=None) -> ft.Control | None:
    """Builds a collapsible accordion showing the model's internal reasoning process.

    Expansion is handled IN PLACE (no parent re-render needed) so the toggle
    always responds instantly, even while background tasks are updating the
    screen version counter.
    """
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

    icon_ref = ft.Ref[ft.Icon]()
    body = ft.Container(
        content=ft.Markdown(
            thought.strip(),
            selectable=True,
            extension_set=ft.MarkdownExtensionSet.GITHUB_FLAVORED,
        ),
        padding=ft.Padding(
            tokens.SPACE_SM, tokens.SPACE_XS, tokens.SPACE_SM, tokens.SPACE_XS
        ),
        bgcolor=ft.Colors.with_opacity(tokens.OPACITY_SUBTLE, ft.Colors.ON_SURFACE),
        border_radius=tokens.RADIUS_SM,
        border=ft.Border.all(
            tokens.DIVIDER_THICKNESS,
            ft.Colors.with_opacity(tokens.OPACITY_MUTED, ft.Colors.ON_SURFACE),
        ),
        visible=show_thought,
    )

    def _apply_state(expanded: bool):
        if hasattr(body, "_frozen"):
            try:
                del body._frozen
            except AttributeError:
                pass
        body.visible = expanded
        if icon_ref.current:
            if hasattr(icon_ref.current, "_frozen"):
                try:
                    del icon_ref.current._frozen
                except AttributeError:
                    pass
            icon_ref.current.icon = (
                ft.Icons.KEYBOARD_ARROW_UP_ROUNDED
                if expanded
                else ft.Icons.KEYBOARD_ARROW_DOWN_ROUNDED
            )

    def _toggle(_):
        expanded = not block.get("_show_thought", False)
        block["_show_thought"] = expanded
        if on_change:
            on_change()
            return
        _apply_state(expanded)
        try:
            body.update()
            if icon_ref.current:
                icon_ref.current.update()
        except Exception:
            pass

    toggle_btn = ft.Container(
        content=ft.Row(
            controls=[
                ft.Row(
                    [
                        ft.Icon(
                            ft.Icons.PSYCHOLOGY_ROUNDED,
                            size=tokens.ICON_XS,
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
                    ref=icon_ref,
                    icon=ft.Icons.KEYBOARD_ARROW_UP_ROUNDED
                    if show_thought
                    else ft.Icons.KEYBOARD_ARROW_DOWN_ROUNDED,
                    size=tokens.ICON_SM,
                    color=ft.Colors.ON_SURFACE_VARIANT,
                ),
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        ),
        padding=ft.Padding(
            tokens.SPACE_SM, tokens.SPACE_XXS, tokens.SPACE_SM, tokens.SPACE_XXS
        ),
        bgcolor=ft.Colors.with_opacity(tokens.OPACITY_SUBTLE, theme.PRIMARY),
        border_radius=tokens.RADIUS_SM,
        on_click=_toggle,
        ink=True,
    )

    return ft.Column(
        [toggle_btn, body],
        spacing=tokens.SPACE_XXS,
    )
