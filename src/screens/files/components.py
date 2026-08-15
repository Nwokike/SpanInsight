"""Filesystem UI components: breadcrumbs, action bar, empty states for Files screen."""

from __future__ import annotations

import os

import flet as ft

from core import theme, tokens

_DATA_EXTENSIONS = {
    ".csv",
    ".xlsx",
    ".xls",
    ".json",
    ".parquet",
    ".tsv",
    ".feather",
    ".orc",
    ".db",
    ".sqlite",
}


def fmt_size(size_bytes) -> str:
    """Format file bytes into human-readable B / KB / MB string."""
    if size_bytes is None:
        return ""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    if size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    return f"{size_bytes / (1024 * 1024):.1f} MB"


def is_data_file(name: str) -> bool:
    """Check if file is tabular dataset eligible for direct Analysis loading."""
    _, ext = os.path.splitext(name.lower())
    return ext in _DATA_EXTENSIONS


def build_no_session_view(on_go_to_analysis) -> ft.Control:
    """Splash shown when no active Colab VM session exists."""
    return ft.Container(
        content=ft.Column(
            [
                ft.Icon(
                    ft.Icons.CLOUD_OFF_ROUNDED,
                    size=64,
                    color=ft.Colors.ON_SURFACE_VARIANT,
                ),
                ft.Text(
                    "No active session",
                    size=tokens.FONT_XL,
                    weight=ft.FontWeight.W_600,
                ),
                ft.Text(
                    "Start a Colab session from the Analysis tab first.",
                    color=ft.Colors.ON_SURFACE_VARIANT,
                    text_align=ft.TextAlign.CENTER,
                ),
                ft.FilledButton(
                    "Go to Analysis",
                    icon=ft.Icons.ANALYTICS_ROUNDED,
                    on_click=on_go_to_analysis,
                ),
            ],
            alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=tokens.SPACE_MD,
        ),
        expand=True,
        alignment=ft.Alignment.CENTER,
        padding=tokens.SPACE_XL,
    )


def build_empty_dir_view(on_upload) -> ft.Control:
    """Centered placeholder when current directory has zero files."""
    return ft.Container(
        content=ft.Column(
            [
                ft.Icon(
                    ft.Icons.FOLDER_OPEN_ROUNDED,
                    size=56,
                    color=ft.Colors.with_opacity(0.2, ft.Colors.ON_SURFACE),
                ),
                ft.Text(
                    "Empty directory",
                    size=tokens.FONT_LG,
                    color=ft.Colors.ON_SURFACE_VARIANT,
                ),
                ft.FilledTonalButton(
                    "Upload a file",
                    icon=ft.Icons.UPLOAD_ROUNDED,
                    on_click=on_upload,
                ),
            ],
            alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=tokens.SPACE_MD,
        ),
        alignment=ft.Alignment.CENTER,
        expand=True,
    )


def build_breadcrumbs(
    current_path: str,
    on_navigate=None,
    set_current_path=None,
) -> ft.Control:
    """Interactive POSIX directory path breadcrumbs."""
    nav_fn = on_navigate or set_current_path or (lambda p: None)
    parts = [p for p in current_path.strip("/").split("/") if p]
    controls: list[ft.Control] = [
        ft.TextButton(
            "/",
            on_click=lambda _: nav_fn("/content"),
            style=ft.ButtonStyle(
                padding=ft.Padding(4, 2, 4, 2),
                color=theme.PRIMARY,
            ),
        )
    ]
    acc = ""
    for part in parts:
        acc += f"/{part}"
        curr = acc
        controls.append(
            ft.Icon(
                ft.Icons.CHEVRON_RIGHT_ROUNDED,
                size=tokens.ICON_SM,
                color=ft.Colors.ON_SURFACE_VARIANT,
            )
        )
        controls.append(
            ft.TextButton(
                part,
                on_click=lambda _, p=curr: nav_fn(p),
                style=ft.ButtonStyle(
                    padding=ft.Padding(4, 2, 4, 2),
                    color=theme.PRIMARY,
                ),
            )
        )
    return ft.Row(
        controls=controls,
        spacing=0,
        scroll=ft.ScrollMode.AUTO,
    )
