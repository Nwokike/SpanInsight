"""Data management and reset settings section.

Shows the local dataset cache size and provides tiles to:
  - Clear locally-cached dataset files (stored by dataset_cache.py)
  - Clear all local app settings/preferences
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

import flet as ft

from core import theme, tokens
from core.styles import section_header, setting_tile

logger = logging.getLogger("DataSection")


def _get_cache_stats() -> tuple[int, str]:
    """Return (file_count, human_readable_size) for the local dataset cache."""
    try:
        storage_env = os.getenv("FLET_APP_STORAGE_DATA")
        cache_dir = (
            Path(storage_env) / "datasets"
            if storage_env
            else Path(".flet") / "storage" / "data" / "datasets"
        )
        if not cache_dir.exists():
            return 0, "0 B"
        files = [f for f in cache_dir.iterdir() if f.is_file()]
        total = sum(f.stat().st_size for f in files)
        size_str = total
        for unit in ("B", "KB", "MB", "GB"):
            if size_str < 1024:
                return len(files), f"{size_str:.0f} {unit}"
            size_str /= 1024
        return len(files), f"{size_str:.1f} GB"
    except Exception:
        return 0, "Unknown"


def build_data_section(
    on_clear_data,
    on_clear_dataset_cache=None,
) -> list[ft.Control]:
    """Local cache info, dataset cache clear, and preferences reset tiles."""
    cache_count, cache_size = _get_cache_stats()
    cache_subtitle = (
        f"{cache_count} file{'s' if cache_count != 1 else ''} · {cache_size}"
        if cache_count > 0
        else "No locally cached datasets"
    )

    controls: list[ft.Control] = [
        section_header("Data Management"),
        ft.Container(
            content=ft.Row(
                [
                    ft.Container(
                        content=ft.Icon(
                            ft.Icons.FOLDER_ROUNDED,
                            size=tokens.ICON_MD,
                            color=theme.ACCENT,
                        ),
                        padding=tokens.SPACE_SM,
                        border_radius=tokens.RADIUS_SM,
                        bgcolor=ft.Colors.with_opacity(
                            tokens.OPACITY_LIGHT, theme.ACCENT
                        ),
                    ),
                    ft.Column(
                        [
                            ft.Text(
                                "Local Dataset Cache",
                                size=tokens.FONT_SM,
                                weight=ft.FontWeight.W_600,
                            ),
                            ft.Text(
                                cache_subtitle,
                                size=tokens.FONT_XS,
                                color=ft.Colors.ON_SURFACE_VARIANT,
                            ),
                        ],
                        spacing=tokens.SPACE_TINY,
                        expand=True,
                    ),
                    ft.TextButton(
                        "Clear Cache",
                        icon=ft.Icons.DELETE_OUTLINE_ROUNDED,
                        style=ft.ButtonStyle(
                            color=theme.ERROR,
                            padding=ft.Padding(
                                tokens.SPACE_SM,
                                tokens.SPACE_XS,
                                tokens.SPACE_SM,
                                tokens.SPACE_XS,
                            ),
                        ),
                        on_click=on_clear_dataset_cache,
                        disabled=(cache_count == 0 or on_clear_dataset_cache is None),
                        visible=True,
                    ),
                ],
                spacing=tokens.SPACE_SM,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            padding=ft.Padding(
                tokens.SPACE_MD,
                tokens.SPACE_SM,
                tokens.SPACE_MD,
                tokens.SPACE_SM,
            ),
            border_radius=tokens.RADIUS_MD,
            bgcolor=ft.Colors.with_opacity(tokens.OPACITY_SUBTLE, ft.Colors.ON_SURFACE),
            border=ft.Border.all(
                tokens.DIVIDER_THICKNESS,
                ft.Colors.with_opacity(tokens.OPACITY_MUTED, ft.Colors.ON_SURFACE),
            ),
        ),
        setting_tile(
            icon=ft.Icons.SETTINGS_BACKUP_RESTORE_ROUNDED,
            title="Clear Local Settings",
            subtitle="Reset preferences (Colab account unaffected)",
            on_click=on_clear_data,
        ),
    ]

    return controls
