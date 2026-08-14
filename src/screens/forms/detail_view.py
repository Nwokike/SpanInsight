"""Form detail and submissions response view component for Forms screen."""

from __future__ import annotations

import json

import flet as ft

from components.form_editor import TYPE_ICONS
from core import theme, utils


def build_form_detail_view(
    page: ft.Page,
    form: dict,
    on_back,
    on_copy_link,
    on_renew,
    on_download_csv,
    on_analyze,
    on_delete,
) -> ft.Control:
    """Detailed summary of form fields, expiration, link sharing, and submitted data table."""
    if not form:
        return ft.Container()

    controls = []
    controls.append(
        ft.Container(
            content=ft.Row(
                [
                    ft.IconButton(ft.Icons.ARROW_BACK_ROUNDED, on_click=on_back),
                    ft.Text(form["title"], weight="bold", size=16, expand=True),
                ]
            ),
            padding=ft.Padding(20, 0, 20, 0),
        )
    )
    resp_count = form.get("_count", form.get("response_count", 0))
    controls.append(
        ft.Container(
            content=ft.Column(
                [
                    ft.Row(
                        [
                            ft.Icon(
                                ft.Icons.PEOPLE_ROUNDED, size=16, color=theme.ACCENT
                            ),
                            ft.Text(f"{resp_count} responses", weight="w500"),
                        ],
                        spacing=8,
                    ),
                    ft.Row(
                        [
                            ft.Icon(
                                ft.Icons.TIMER_ROUNDED, size=16, color=theme.WARNING
                            ),
                            ft.Text(
                                f"Expires: {form.get('expires_at', '')[:10]}",
                                size=12,
                            ),
                        ],
                        spacing=8,
                    ),
                ],
                spacing=8,
            ),
            padding=16,
            margin=ft.Margin(20, 8, 20, 8),
            border_radius=12,
            bgcolor=theme.GLASS_BG,
            border=ft.Border.all(1, theme.GLASS_BORDER_COLOR),
        )
    )

    schema_json = form.get("schema_json", "")
    fields = []
    if isinstance(schema_json, str) and schema_json:
        try:
            fields = json.loads(schema_json)
        except Exception:
            pass
    elif isinstance(schema_json, list):
        fields = schema_json

    if fields:
        field_controls = []
        for idx, field in enumerate(fields):
            label = field.get("label", field.get("name", f"Field {idx + 1}"))
            ftype = field.get("type", "text")
            required = field.get("required", False)
            options = field.get("options", [])
            field_controls.append(
                ft.Container(
                    content=ft.Row(
                        [
                            ft.Icon(
                                TYPE_ICONS.get(ftype, ft.Icons.TEXT_FIELDS),
                                size=16,
                                color=theme.ACCENT,
                            ),
                            ft.Column(
                                [
                                    ft.Row(
                                        [
                                            ft.Text(
                                                label,
                                                size=13,
                                                weight="w500",
                                                expand=True,
                                            ),
                                            ft.Container(
                                                content=ft.Text(
                                                    ftype.upper(),
                                                    size=9,
                                                    color=theme.PRIMARY,
                                                    weight="bold",
                                                ),
                                                padding=ft.Padding(6, 2, 6, 2),
                                                border_radius=4,
                                                bgcolor=ft.Colors.with_opacity(
                                                    0.08, theme.PRIMARY
                                                ),
                                            ),
                                            ft.Text(
                                                "*",
                                                size=14,
                                                color=theme.ERROR,
                                                weight="bold",
                                            )
                                            if required
                                            else ft.Container(),
                                        ],
                                        spacing=6,
                                    ),
                                    ft.Text(
                                        ", ".join(options[:5]),
                                        size=10,
                                        color=ft.Colors.ON_SURFACE_VARIANT,
                                        max_lines=1,
                                        overflow="ellipsis",
                                    )
                                    if options
                                    else ft.Container(),
                                ],
                                spacing=2,
                                expand=True,
                            ),
                        ],
                        spacing=10,
                        vertical_alignment="start",
                    ),
                    padding=ft.Padding(12, 8, 12, 8),
                    border_radius=8,
                    bgcolor=ft.Colors.with_opacity(0.03, ft.Colors.ON_SURFACE),
                )
            )
        controls.append(
            ft.Container(
                content=ft.Column(
                    [
                        ft.Text(f"Form Fields ({len(fields)})", weight="bold", size=13),
                        ft.Column(field_controls, spacing=4),
                    ],
                    spacing=8,
                ),
                padding=ft.Padding(20, 8, 20, 8),
            )
        )

    controls.append(
        ft.Container(
            content=ft.Column(
                [
                    ft.Row(
                        [
                            ft.FilledButton(
                                "Copy Link",
                                icon=ft.Icons.LINK_ROUNDED,
                                style=ft.ButtonStyle(
                                    bgcolor=theme.PRIMARY,
                                    color=ft.Colors.WHITE,
                                    shape=ft.RoundedRectangleBorder(radius=12),
                                    padding=14,
                                ),
                                on_click=lambda _: on_copy_link(form["id"]),
                            ),
                            ft.FilledButton(
                                "Renew +7d",
                                icon=ft.Icons.UPDATE_ROUNDED,
                                style=ft.ButtonStyle(
                                    bgcolor=theme.PRIMARY,
                                    color=ft.Colors.WHITE,
                                    shape=ft.RoundedRectangleBorder(radius=12),
                                    padding=14,
                                ),
                                on_click=lambda _: on_renew(form["id"]),
                            ),
                        ],
                        spacing=8,
                        wrap=True,
                    ),
                    ft.Row(
                        [
                            ft.FilledButton(
                                "Download CSV",
                                icon=ft.Icons.DOWNLOAD_ROUNDED,
                                style=ft.ButtonStyle(
                                    bgcolor=theme.PRIMARY,
                                    color=ft.Colors.WHITE,
                                    shape=ft.RoundedRectangleBorder(radius=12),
                                    padding=14,
                                ),
                                on_click=lambda _: on_download_csv(form),
                            ),
                            ft.FilledButton(
                                "Analyze",
                                icon=ft.Icons.ANALYTICS_ROUNDED,
                                style=ft.ButtonStyle(
                                    bgcolor=theme.PRIMARY,
                                    color=ft.Colors.WHITE,
                                    shape=ft.RoundedRectangleBorder(radius=12),
                                    padding=14,
                                ),
                                on_click=lambda _: on_analyze(form),
                            ),
                        ],
                        spacing=8,
                        wrap=True,
                    ),
                    ft.TextButton(
                        "Delete Form",
                        icon=ft.Icons.DELETE_OUTLINE_ROUNDED,
                        style=ft.ButtonStyle(
                            color=theme.ERROR,
                            shape=ft.RoundedRectangleBorder(radius=12),
                        ),
                        on_click=lambda _: on_delete(form["id"]),
                    ),
                ],
                spacing=8,
            ),
            padding=ft.Padding(20, 8, 20, 8),
        )
    )

    responses = form.get("_responses", [])
    if responses:
        rows_data = [r["data"] for r in responses[:50]]
        if rows_data:
            columns = []
            for row in rows_data:
                for key in row:
                    if key not in columns:
                        columns.append(key)

            controls.append(
                ft.Container(
                    content=ft.Column(
                        [
                            ft.Text(
                                f"Latest {min(50, len(responses))} Responses",
                                weight="bold",
                                size=13,
                            ),
                            ft.DataTable(
                                columns=[
                                    ft.DataColumn(ft.Text(c, size=11)) for c in columns
                                ],
                                rows=[
                                    ft.DataRow(
                                        cells=[
                                            ft.DataCell(
                                                ft.Text(str(row.get(c, "")), size=11)
                                            )
                                            for c in columns
                                        ]
                                    )
                                    for row in rows_data
                                ],
                                column_spacing=16,
                                horizontal_lines=ft.BorderSide(
                                    0.5, ft.Colors.OUTLINE_VARIANT
                                ),
                            ),
                        ],
                        spacing=8,
                    ),
                    padding=ft.Padding(20, 8, 20, 8),
                )
            )

    if page and page.platform in (ft.PagePlatform.ANDROID, ft.PagePlatform.IOS):
        controls.append(
            ft.Container(
                content=ft.Column(
                    [
                        ft.Text(
                            "SPONSORED",
                            size=8,
                            weight=ft.FontWeight.W_700,
                            color=ft.Colors.ON_SURFACE_VARIANT,
                            style=ft.TextStyle(letter_spacing=1),
                        ),
                        utils.get_banner_ad(),
                    ],
                    horizontal_alignment="center",
                    spacing=4,
                ),
                alignment=ft.Alignment.CENTER,
                padding=8,
                border_radius=12,
                bgcolor=theme.GLASS_BG,
                border=ft.Border.all(1, theme.GLASS_BORDER_COLOR),
                margin=ft.Margin(20, 8, 20, 8),
            )
        )

    controls.append(ft.Container(height=100))
    return ft.Column(controls)
