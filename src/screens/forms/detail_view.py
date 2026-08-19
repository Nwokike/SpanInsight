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
) -> list[ft.Control]:
    """Detailed summary of form fields, expiration, link sharing, and submitted data table."""
    if not form:
        return []

    resp_count = form.get("_count", form.get("response_count", 0))
    expires_at = form.get("expires_at", "")[:10]
    schema_json = form.get("schema_json", "")

    fields = []
    if isinstance(schema_json, str) and schema_json:
        try:
            fields = json.loads(schema_json)
        except Exception:
            pass
    elif isinstance(schema_json, list):
        fields = schema_json

    controls = []

    # 1. Header Row
    controls.append(
        ft.Container(
            content=ft.Row(
                [
                    ft.IconButton(
                        ft.Icons.ARROW_BACK_ROUNDED,
                        tooltip="Back to Forms",
                        on_click=on_back,
                        style=ft.ButtonStyle(padding=tokens.SPACE_XXS),
                    ),
                    ft.Text(
                        form.get("title", "Form Detail"),
                        weight=ft.FontWeight.BOLD,
                        size=tokens.FONT_HEADING,
                        expand=True,
                    ),
                    ft.Container(
                        content=ft.Row(
                            [
                                ft.Container(
                                    width=7,
                                    height=7,
                                    border_radius=4,
                                    bgcolor=theme.SUCCESS
                                    if form.get("is_active", 1)
                                    else theme.WARNING,
                                ),
                                ft.Text(
                                    "Active"
                                    if form.get("is_active", 1)
                                    else "Inactive",
                                    size=tokens.FONT_XS,
                                    weight=ft.FontWeight.W_600,
                                    color=theme.SUCCESS
                                    if form.get("is_active", 1)
                                    else theme.WARNING,
                                ),
                            ],
                            spacing=tokens.SPACE_XXS,
                            alignment=ft.MainAxisAlignment.CENTER,
                        ),
                        padding=ft.Padding(
                            tokens.SPACE_SM,
                            tokens.SPACE_XXS,
                            tokens.SPACE_SM,
                            tokens.SPACE_XXS,
                        ),
                        border_radius=tokens.RADIUS_SM,
                        bgcolor=ft.Colors.with_opacity(
                            tokens.OPACITY_MUTED,
                            theme.SUCCESS
                            if form.get("is_active", 1)
                            else theme.WARNING,
                        ),
                    ),
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            padding=ft.Padding(
                tokens.SPACE_XL,
                tokens.SPACE_SM,
                tokens.SPACE_XL,
                tokens.SPACE_NONE,
            ),
        )
    )

    # 2. Metadata / Summary Glass Bar
    meta_pills = [
        ft.Container(
            content=ft.Row(
                [
                    ft.Icon(
                        ft.Icons.PEOPLE_ROUNDED,
                        size=tokens.ICON_SM,
                        color=theme.ACCENT,
                    ),
                    ft.Text(
                        f"{resp_count} {'response' if resp_count == 1 else 'responses'}",
                        size=tokens.FONT_SM,
                        weight=ft.FontWeight.W_600,
                        color=ft.Colors.ON_SURFACE,
                    ),
                ],
                spacing=tokens.SPACE_XS,
            ),
            padding=ft.Padding(
                tokens.SPACE_MD_SM,
                tokens.SPACE_XS,
                tokens.SPACE_MD_SM,
                tokens.SPACE_XS,
            ),
            border_radius=tokens.RADIUS_SM,
            bgcolor=ft.Colors.with_opacity(tokens.OPACITY_MUTED, theme.ACCENT),
        ),
        ft.Container(
            content=ft.Row(
                [
                    ft.Icon(
                        ft.Icons.TIMER_ROUNDED,
                        size=tokens.ICON_SM,
                        color=theme.WARNING,
                    ),
                    ft.Text(
                        f"Expires {expires_at}" if expires_at else "No Expiry",
                        size=tokens.FONT_SM,
                        weight=ft.FontWeight.W_500,
                        color=ft.Colors.ON_SURFACE,
                    ),
                ],
                spacing=tokens.SPACE_XS,
            ),
            padding=ft.Padding(
                tokens.SPACE_MD_SM,
                tokens.SPACE_XS,
                tokens.SPACE_MD_SM,
                tokens.SPACE_XS,
            ),
            border_radius=tokens.RADIUS_SM,
            bgcolor=ft.Colors.with_opacity(tokens.OPACITY_MUTED, theme.WARNING),
        ),
        ft.Container(
            content=ft.Row(
                [
                    ft.Icon(
                        ft.Icons.FORMAT_LIST_BULLETED_ROUNDED,
                        size=tokens.ICON_SM,
                        color=theme.PRIMARY,
                    ),
                    ft.Text(
                        f"{len(fields)} {'field' if len(fields) == 1 else 'fields'}",
                        size=tokens.FONT_SM,
                        weight=ft.FontWeight.W_500,
                        color=ft.Colors.ON_SURFACE,
                    ),
                ],
                spacing=tokens.SPACE_XS,
            ),
            padding=ft.Padding(
                tokens.SPACE_MD_SM,
                tokens.SPACE_XS,
                tokens.SPACE_MD_SM,
                tokens.SPACE_XS,
            ),
            border_radius=tokens.RADIUS_SM,
            bgcolor=ft.Colors.with_opacity(tokens.OPACITY_MUTED, theme.PRIMARY),
        ),
    ]

    desc_text = form.get("description", "").strip()

    controls.append(
        ft.Container(
            content=ft.Column(
                [
                    ft.Row(meta_pills, spacing=tokens.SPACE_SM, wrap=True),
                    ft.Text(
                        desc_text,
                        size=tokens.FONT_BODY_SM,
                        color=ft.Colors.ON_SURFACE_VARIANT,
                    )
                    if desc_text
                    else ft.Container(),
                ],
                spacing=tokens.SPACE_SM,
            ),
            padding=tokens.SPACE_MD,
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

    # 3. Sleek Action Toolbar (Primary, Outlined, Danger hierarchy)
    has_responses = resp_count > 0

    button_shape = ft.RoundedRectangleBorder(radius=tokens.RADIUS_MD_SM)
    btn_padding = ft.Padding(
        tokens.SPACE_MD, tokens.SPACE_SM, tokens.SPACE_MD, tokens.SPACE_SM
    )

    action_buttons = [
        # Primary Action: Copy Link
        ft.FilledButton(
            "Copy Link",
            icon=ft.Icons.LINK_ROUNDED,
            style=ft.ButtonStyle(
                bgcolor=theme.PRIMARY,
                color=ft.Colors.WHITE,
                shape=button_shape,
                padding=btn_padding,
            ),
            on_click=lambda _: on_copy_link(form["id"]),
        ),
        # Secondary: Analyze in Notebook
        ft.OutlinedButton(
            "Analyze in Notebook",
            icon=ft.Icons.ANALYTICS_ROUNDED,
            disabled=not has_responses,
            tooltip="Analyze response data in analysis session"
            if has_responses
            else "Collect responses first to analyze",
            style=ft.ButtonStyle(
                shape=button_shape,
                padding=btn_padding,
            ),
            on_click=lambda _: on_analyze(form),
        ),
        # Secondary: Export CSV
        ft.OutlinedButton(
            "Export CSV",
            icon=ft.Icons.DOWNLOAD_ROUNDED,
            disabled=not has_responses,
            tooltip="Download all submitted responses as CSV"
            if has_responses
            else "No responses to export yet",
            style=ft.ButtonStyle(
                shape=button_shape,
                padding=btn_padding,
            ),
            on_click=lambda _: on_download_csv(form),
        ),
        # Secondary: Renew Form (+7 Days)
        ft.OutlinedButton(
            "Renew (+7d)",
            icon=ft.Icons.UPDATE_ROUNDED,
            tooltip="Extend form availability by 7 days",
            style=ft.ButtonStyle(
                shape=button_shape,
                padding=btn_padding,
            ),
            on_click=lambda _: on_renew(form["id"]),
        ),
        # Destructive: Delete Form
        ft.TextButton(
            "Delete Form",
            icon=ft.Icons.DELETE_OUTLINE_ROUNDED,
            tooltip="Permanently delete this form and collected responses",
            style=ft.ButtonStyle(
                color=theme.ERROR,
                shape=button_shape,
                padding=btn_padding,
            ),
            on_click=lambda _: on_delete(form["id"]),
        ),
    ]

    controls.append(
        ft.Container(
            content=ft.Row(
                action_buttons,
                spacing=tokens.SPACE_SM,
                wrap=True,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            padding=ft.Padding(
                tokens.SPACE_XL,
                tokens.SPACE_XS,
                tokens.SPACE_XL,
                tokens.SPACE_SM,
            ),
        )
    )

    # 4. Form Fields Preview Section
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
                            f"Survey Schema ({len(fields)} {'Question' if len(fields) == 1 else 'Questions'})",
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

    # 5. Responses Table or Sleek Empty State
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
                            ft.Row(
                                [
                                    ft.Text(
                                        f"Latest Responses ({min(50, len(responses))})",
                                        weight="bold",
                                        size=tokens.FONT_BODY,
                                        expand=True,
                                    ),
                                    ft.Text(
                                        f"Showing top {min(50, len(responses))}",
                                        size=tokens.FONT_XS,
                                        color=ft.Colors.ON_SURFACE_VARIANT,
                                    ),
                                ],
                                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                            ),
                            ft.Container(
                                content=ft.Row(
                                    controls=[
                                        ft.DataTable(
                                            columns=[
                                                ft.DataColumn(
                                                    ft.Text(
                                                        c,
                                                        size=tokens.FONT_SM,
                                                        weight=ft.FontWeight.W_600,
                                                    )
                                                )
                                                for c in columns
                                            ],
                                            rows=[
                                                ft.DataRow(
                                                    cells=[
                                                        ft.DataCell(
                                                            ft.Text(
                                                                str(row.get(c, "-")),
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
                                        )
                                    ],
                                    scroll=ft.ScrollMode.AUTO,
                                ),
                                border_radius=tokens.RADIUS_MD,
                                border=ft.Border.all(
                                    tokens.DIVIDER_THICKNESS,
                                    theme.GLASS_BORDER_COLOR,
                                ),
                                padding=tokens.SPACE_SM,
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
    else:
        # Zero-response elegant empty state
        controls.append(
            ft.Container(
                content=ft.Column(
                    [
                        ft.Icon(
                            ft.Icons.QUERY_STATS_ROUNDED,
                            size=tokens.ICON_XL,
                            color=ft.Colors.with_opacity(
                                tokens.OPACITY_MUTED, theme.PRIMARY
                            ),
                        ),
                        ft.Text(
                            "No responses yet",
                            weight=ft.FontWeight.W_600,
                            size=tokens.FONT_BODY,
                            color=ft.Colors.ON_SURFACE,
                        ),
                        ft.Text(
                            "Share your survey link to start collecting submissions in real time.",
                            size=tokens.FONT_BODY_SM,
                            color=ft.Colors.ON_SURFACE_VARIANT,
                            text_align=ft.TextAlign.CENTER,
                        ),
                    ],
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=tokens.SPACE_XS,
                ),
                padding=tokens.SPACE_XL,
                margin=ft.Margin(
                    tokens.SPACE_XL,
                    tokens.SPACE_SM,
                    tokens.SPACE_XL,
                    tokens.SPACE_SM,
                ),
                alignment=ft.Alignment.CENTER,
                border_radius=tokens.RADIUS_MD,
                bgcolor=theme.GLASS_BG,
                border=ft.Border.all(
                    tokens.DIVIDER_THICKNESS, theme.GLASS_BORDER_COLOR
                ),
            )
        )

    # 6. Mobile Ad slot (if mobile)
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
    return controls
