"""Reusable refresh button component.

Mirrors the style used in the Forms dashboard - a TextButton with
a refresh icon and label.  Drop this anywhere a "Refresh" action is
needed so the look-and-feel stays consistent across the app.
"""

from __future__ import annotations

import flet as ft


def build_refresh_button(on_click, label: str = "Refresh") -> ft.TextButton:
    """Return a styled refresh TextButton.

    Args:
        on_click: The callback to invoke when the button is pressed.
                  Typically ``lambda e: page.run_task(load_something)``.
        label:    Button text shown next to the icon (default ``"Refresh"``).
    """
    return ft.TextButton(
        label,
        icon=ft.Icons.REFRESH_ROUNDED,
        on_click=on_click,
    )
