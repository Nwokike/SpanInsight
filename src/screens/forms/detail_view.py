"""Form detail and submissions response view component for Forms screen."""

from __future__ import annotations

import json

import flet as ft

from components.form_editor import TYPE_ICONS
from core import theme, tokens, utils


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
                    ft.Text(
                        form["title"],
                        weight="bold",
                        size=tokens.FONT_HEADING,
                        expand=True,
                    ),
                ]
            ),
            padding=ft.Padding(
                tokens.SPACE_XL,
                tokens.SPACE_NONE,
                tokens.SPACE_XL,
                tokens.SPACE_NONE,
            ),
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
                                ft.Icons.PEOPLE_ROUNDED,
                                size=tokens.ICON_SM,
                                color=theme.ACCENT,
                            ),
                            ft.Text(
                                f"{resp_count} responses",
                                weight=ft.FontWeight.W_500,
                            ),
                        ],
                        spacing=tokens.SPACE_SM,
                    ),
                    ft.Row(
                        [
                            ft.Icon(
                                ft.Icons.TIMER_ROUNDED,
                                size=tokens.ICON_SM,
                                color=theme.WARNING,
                            ),
                            ft.Text(
                                f"Expires: {form.get('expires_at', '')[:10]}",
                                size=tokens.FONT_BODY_SM,
                            ),
                        ],
                        spacing=tokens.SPACE_SM,
                    ),
                ],
                spacing=tokens.SPACE_SM,
            ),
            padding=tokens.SPACE_LG,
            margin=ft.Margin(
                tokens.SPACE_XL,
                tokens.SPACE_SM,
                tokens.SPACE_XL,
                tokens.SPACE_SM,
            ),
            border_radius=tokens.RADIUS_MD,
            bgcolor=theme.GLASS_BG,
            border=ft.Border.all(tokens.DIVIDER_THICKNESS, theme.GLASS_BORDER_COLOR),
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
                                size=tokens.ICON_SM,
                                color=theme.ACCENT,
                            ),
                            ft.Column(
                                [
                                    ft.Row(
                                        [
                                            ft.Text(
                                                label,
                                                size=tokens.FONT_BODY,
                                                weight=ft.FontWeight.W_500,
                                                expand=True,
                                            ),
                                            ft.Container(
                                                content=ft.Text(
                                                    ftype.upper(),
                                                    size=tokens.FONT_XS,
                                                    color=theme.PRIMARY,
                                                    weight="bold",
                                                ),
                                                padding=ft.Padding(
                                                    tokens.SPACE_SM_XS,
                                                    tokens.SPACE_XXS,
                                                    tokens.SPACE_SM_XS,
                                                    tokens.SPACE_XXS,
                                                ),
                                                border_radius=tokens.RADIUS_XS,
                                                bgcolor=ft.Colors.with_opacity(
                                                    tokens.OPACITY_MUTED,
                                                    theme.PRIMARY,
                                                ),
                                            ),
                                            ft.Text(
                                                "*",
                                                size=tokens.FONT_MD,
                                                color=theme.ERROR,
                                                weight="bold",
                                            )
                                            if required
                                            else ft.Container(),
                                        ],
                                        spacing=tokens.SPACE_SM_XS,
                                    ),
                                    ft.Text(
                                        ", ".join(options[:5]),
                                        size=tokens.FONT_XS,
                                        color=ft.Colors.ON_SURFACE_VARIANT,
                                        max_lines=1,
                                        overflow=ft.TextOverflow.ELLIPSIS,
                                    )
                                    if options
                                    else ft.Container(),
                                ],
                                spacing=tokens.SPACE_XXS,
                                expand=True,
                            ),
                        ],
                        spacing=tokens.SPACE_MD_SM,
                        vertical_alignment=ft.CrossAxisAlignment.START,
                    ),
                    padding=ft.Padding(
                        tokens.SPACE_MD,
                        tokens.SPACE_SM,
                        tokens.SPACE_MD,
                        tokens.SPACE_SM,
                    ),
                    border_radius=tokens.RADIUS_SM,
                    bgcolor=ft.Colors.with_opacity(
                        tokens.OPACITY_SUBTLE, ft.Colors.ON_SURFACE
                    ),
                )
            )
        controls.append(
            ft.Container(
                content=ft.Column(
                    [
                        ft.Text(
                            f"Form Fields ({len(fields)})",
                            weight="bold",
                            size=tokens.FONT_BODY,
                        ),
                        ft.Column(field_controls, spacing=tokens.SPACE_XS),
                    ],
                    spacing=tokens.SPACE_SM,
                ),
                padding=ft.Padding(
                    tokens.SPACE_XL,
                    tokens.SPACE_SM,
                    tokens.SPACE_XL,
                    tokens.SPACE_SM,
                ),
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
                                    shape=ft.RoundedRectangleBorder(
                                        radius=tokens.RADIUS_MD
                                    ),
                                    padding=tokens.BUTTON_PADDING_MD,
                                ),
                                on_click=lambda _: on_copy_link(form["id"]),
                            ),
                            ft.FilledButton(
                                "Renew +7d",
                                icon=ft.Icons.UPDATE_ROUNDED,
                                style=ft.ButtonStyle(
                                    bgcolor=theme.PRIMARY,
                                    color=ft.Colors.WHITE,
                                    shape=ft.RoundedRectangleBorder(
                                        radius=tokens.RADIUS_MD
                                    ),
                                    padding=tokens.BUTTON_PADDING_MD,
                                ),
                                on_click=lambda _: on_renew(form["id"]),
                            ),
                        ],
                        spacing=tokens.SPACE_SM,
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
                                    shape=ft.RoundedRectangleBorder(
                                        radius=tokens.RADIUS_MD
                                    ),
                                    padding=tokens.BUTTON_PADDING_MD,
                                ),
                                on_click=lambda _: on_download_csv(form),
                            ),
                            ft.FilledButton(
                                "Analyze",
                                icon=ft.Icons.ANALYTICS_ROUNDED,
                                style=ft.ButtonStyle(
                                    bgcolor=theme.PRIMARY,
                                    color=ft.Colors.WHITE,
                                    shape=ft.RoundedRectangleBorder(
                                        radius=tokens.RADIUS_MD
                                    ),
                                    padding=tokens.BUTTON_PADDING_MD,
                                ),
                                on_click=lambda _: on_analyze(form),
                            ),
                        ],
                        spacing=tokens.SPACE_SM,
                        wrap=True,
                    ),
                    ft.TextButton(
                        "Delete Form",
                        icon=ft.Icons.DELETE_OUTLINE_ROUNDED,
                        style=ft.ButtonStyle(
                            color=theme.ERROR,
                            shape=ft.RoundedRectangleBorder(radius=tokens.RADIUS_MD),
                        ),
                        on_click=lambda _: on_delete(form["id"]),
                    ),
                ],
                spacing=tokens.SPACE_SM,
            ),
            padding=ft.Padding(
                tokens.SPACE_XL,
                tokens.SPACE_SM,
                tokens.SPACE_XL,
                tokens.SPACE_SM,
            ),
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
                                size=tokens.FONT_BODY,
                            ),
                            ft.DataTable(
                                columns=[
                                    ft.DataColumn(ft.Text(c, size=tokens.FONT_SM))
                                    for c in columns
                                ],
                                rows=[
                                    ft.DataRow(
                                        cells=[
                                            ft.DataCell(
                                                ft.Text(
                                                    str(row.get(c, "")),
                                                    size=tokens.FONT_SM,
                                                )
                                            )
                                            for c in columns
                                        ]
                                    )
                                    for row in rows_data
                                ],
                                column_spacing=tokens.SPACE_LG,
                                horizontal_lines=ft.BorderSide(
                                    tokens.DIVIDER_THICKNESS,
                                    ft.Colors.OUTLINE_VARIANT,
                                ),
                            ),
                        ],
                        spacing=tokens.SPACE_SM,
                    ),
                    padding=ft.Padding(
                        tokens.SPACE_XL,
                        tokens.SPACE_SM,
                        tokens.SPACE_XL,
                        tokens.SPACE_SM,
                    ),
                )
            )

    if page and page.platform in (ft.PagePlatform.ANDROID, ft.PagePlatform.IOS):
        controls.append(
            ft.Container(
                content=ft.Column(
                    [
                        ft.Text(
                            "SPONSORED",
                            size=tokens.FONT_XXS,
                            weight=ft.FontWeight.W_700,
                            color=ft.Colors.ON_SURFACE_VARIANT,
                            style=ft.TextStyle(letter_spacing=1),
                        ),
                        utils.get_banner_ad(),
                    ],
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=tokens.SPACE_XS,
                ),
                alignment=ft.Alignment.CENTER,
                padding=tokens.SPACE_SM,
                border_radius=tokens.RADIUS_MD,
                bgcolor=theme.GLASS_BG,
                border=ft.Border.all(
                    tokens.DIVIDER_THICKNESS, theme.GLASS_BORDER_COLOR
                ),
                margin=ft.Margin(
                    tokens.SPACE_XL,
                    tokens.SPACE_SM,
                    tokens.SPACE_XL,
                    tokens.SPACE_SM,
                ),
            )
        )

    controls.append(ft.Container(height=tokens.INPUT_WIDTH_SM))
    return ft.Column(controls)
