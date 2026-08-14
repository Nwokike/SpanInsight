"""Data management and reset settings section."""

from __future__ import annotations

import flet as ft

from core.styles import section_header, setting_tile


def build_data_section(
    on_clear_data,
) -> list[ft.Control]:
    """Local cache and preferences clear tile."""
    return [
        section_header("Data Management"),
        setting_tile(
            icon=ft.Icons.DELETE_OUTLINE_ROUNDED,
            title="Clear Local Settings",
            subtitle="Reset preferences (Colab account unaffected)",
            on_click=on_clear_data,
        ),
    ]
