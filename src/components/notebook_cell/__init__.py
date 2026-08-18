"""Notebook cell component — compact, modern design for SpanInsight v2.

Each cell is either Code or Markdown. Code cells have:
- Monospace editor with minimal chrome
- Compact play/stop controls
- Auto-sizing output panel with ANSI-colored text and inline images
- Tight action buttons (copy, move, delete)
"""

import flet as ft

from components.notebook_cell.actions import (
    copy_code,
    copy_output,
    fix_with_ai,
    make_actions_row,
)
from components.notebook_cell.output import parse_cell_outputs
from core import theme, tokens


def build_notebook_cell(
    page: ft.Page,
    cell: dict,
    on_run=None,
    on_stop=None,
    on_delete=None,
    on_move_up=None,
    on_move_down=None,
    on_change=None,
    on_clear_output=None,
) -> tuple[ft.Container, dict]:
    """Build a single notebook cell (Code or Markdown).

    Returns (container, refs_dict) where refs_dict holds Ref objects
    for mutable parts (play_btn, stop_row, output, code_input).
    """
    cell_type = cell.get("type", "code")
    source = cell.get("source", "")
    outputs = cell.get("outputs", [])
    is_running = cell.get("is_running", False)

    editor_ref = ft.Ref[ft.TextField]()
    play_btn_ref = ft.Ref[ft.IconButton]()
    stop_row_ref = ft.Ref[ft.Row]()
    output_ref = ft.Ref[ft.ListView]()
    output_panel_ref = ft.Ref[ft.Container]()

    refs = {
        "play_btn": play_btn_ref,
        "stop_row": stop_row_ref,
        "output": output_ref,
        "output_panel": output_panel_ref,
        "code_input": editor_ref,
    }

    def _handle_change(e):
        if editor_ref.current:
            cell["source"] = editor_ref.current.value
            if on_change:
                on_change()

    async def _copy_output(e=None):
        await copy_output(page, cell.get("outputs", []))

    async def _copy_code_task(e=None):
        code_val = editor_ref.current.value if editor_ref.current else source
        await copy_code(page, code_val)

    async def _fix_ai_task(e=None):
        await fix_with_ai(page, cell, on_change)

    def _make_actions():
        last_out = outputs[-1] if outputs else {}
        has_error = (last_out.get("output_type") or last_out.get("type", "")) == "error"
        return make_actions_row(
            on_move_up=on_move_up,
            on_move_down=on_move_down,
            on_delete=on_delete,
            on_copy=lambda: page.run_task(_copy_code_task),
            on_fix=(lambda: page.run_task(_fix_ai_task)) if has_error else None,
        )

    # ── Markdown Cell ────────────────────────────────────────────
    if cell_type == "markdown":
        is_editing = cell.get("is_editing", not bool(source.strip()))
        edit_container = ft.Container(visible=is_editing)
        render_container = ft.Container(visible=not is_editing)
        markdown_ref = ft.Ref[ft.Markdown]()

        def _edit(e=None):
            if not cell.get("is_editing"):
                cell["is_editing"] = True
                edit_container.visible = True
                render_container.visible = False
                if on_change:
                    on_change()
                page.update()

        def _render(e=None):
            if editor_ref.current:
                cell["source"] = editor_ref.current.value
            new_source = cell.get("source", "")
            if markdown_ref.current:
                markdown_ref.current.value = new_source
            cell["is_editing"] = False
            edit_container.visible = False
            render_container.visible = True
            if on_change:
                on_change()
            page.update()

        edit_container.content = ft.Column(
            controls=[
                ft.TextField(
                    ref=editor_ref,
                    value=source,
                    multiline=True,
                    min_lines=2,
                    max_lines=8,
                    text_size=tokens.FONT_SM,
                    border_color=ft.Colors.TRANSPARENT,
                    bgcolor=ft.Colors.TRANSPARENT,
                    on_change=_handle_change,
                    on_blur=_render,
                    hint_text="Type markdown…",
                    content_padding=ft.Padding(
                        tokens.SPACE_SM,
                        tokens.SPACE_XS,
                        tokens.SPACE_SM,
                        tokens.SPACE_XS,
                    ),
                ),
                ft.Row(
                    controls=[
                        ft.Row(
                            controls=[
                                ft.Icon(
                                    ft.Icons.MODE_EDIT_OUTLINE_ROUNDED,
                                    size=tokens.ICON_MICRO,
                                    color=ft.Colors.ON_SURFACE_VARIANT,
                                ),
                                ft.Text(
                                    "Markdown",
                                    size=tokens.FONT_XS,
                                    color=ft.Colors.ON_SURFACE_VARIANT,
                                    weight=ft.FontWeight.W_600,
                                ),
                            ],
                            spacing=tokens.SPACE_XS,
                        ),
                        ft.Container(expand=True),
                        ft.IconButton(
                            icon=ft.Icons.CHECK_ROUNDED,
                            icon_size=tokens.ICON_XS,
                            icon_color=theme.SUCCESS,
                            tooltip="Render",
                            style=ft.ButtonStyle(padding=tokens.SPACE_XS),
                            on_click=_render,
                        ),
                        _make_actions(),
                    ],
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
            ],
            spacing=tokens.SPACE_NONE,
        )

        render_container.content = ft.Column(
            controls=[
                ft.GestureDetector(
                    on_tap=_edit,
                    content=ft.Container(
                        content=ft.Markdown(
                            ref=markdown_ref,
                            value=source,
                            extension_set=ft.MarkdownExtensionSet.GITHUB_WEB,
                            selectable=True,
                        ),
                        padding=tokens.SPACE_SM,
                        expand=True,
                        width=float("inf"),
                    ),
                ),
                ft.Container(
                    content=ft.Row(
                        controls=[
                            ft.Container(expand=True),
                            ft.IconButton(
                                ft.Icons.EDIT_ROUNDED,
                                icon_size=tokens.ICON_XS,
                                tooltip="Edit",
                                style=ft.ButtonStyle(padding=tokens.SPACE_XS),
                                on_click=_edit,
                            ),
                            _make_actions(),
                        ],
                        alignment=ft.MainAxisAlignment.END,
                    ),
                    padding=ft.Padding(
                        tokens.SPACE_SM,
                        tokens.SPACE_NONE,
                        tokens.SPACE_SM,
                        tokens.SPACE_XS,
                    ),
                ),
            ],
            spacing=tokens.SPACE_NONE,
        )

        content = ft.Column(
            [edit_container, render_container], spacing=tokens.SPACE_NONE
        )

        return ft.Container(
            content=content,
            border_radius=tokens.RADIUS_SM,
            bgcolor=ft.Colors.with_opacity(tokens.OPACITY_SUBTLE, ft.Colors.ON_SURFACE),
            border=ft.Border.all(
                tokens.DIVIDER_THICKNESS,
                ft.Colors.with_opacity(tokens.OPACITY_MUTED, ft.Colors.ON_SURFACE),
            ),
            margin=ft.Margin(
                tokens.SPACE_NONE, tokens.SPACE_XS, tokens.SPACE_NONE, tokens.SPACE_XS
            ),
        ), refs

    # ── Code Cell ────────────────────────────────────────────────
    output_controls = parse_cell_outputs(cell)

    output_panel = ft.Container(
        ref=output_panel_ref,
        content=ft.Column(
            controls=[
                ft.Container(
                    content=ft.Column(
                        ref=output_ref,
                        controls=output_controls,
                        spacing=tokens.SPACE_XXS,
                    ),
                    padding=ft.Padding(
                        tokens.SPACE_SM,
                        tokens.SPACE_SM,
                        tokens.SPACE_SM,
                        tokens.SPACE_SM,
                    ),
                ),
                ft.Row(
                    controls=[
                        ft.Text(
                            "OUTPUT",
                            size=tokens.FONT_XXS,
                            color=ft.Colors.with_opacity(
                                tokens.OPACITY_DISABLED, ft.Colors.ON_SURFACE
                            ),
                            weight=ft.FontWeight.W_600,
                        ),
                        ft.Row(
                            controls=[
                                ft.IconButton(
                                    ft.Icons.COPY_ALL_ROUNDED,
                                    icon_size=tokens.ICON_MICRO,
                                    tooltip="Copy Output",
                                    style=ft.ButtonStyle(padding=tokens.SPACE_XXS),
                                    on_click=lambda e: page.run_task(_copy_output, e),
                                ),
                                ft.IconButton(
                                    ft.Icons.CLEAR_ALL_ROUNDED,
                                    icon_size=tokens.ICON_MICRO,
                                    tooltip="Clear Output",
                                    style=ft.ButtonStyle(padding=tokens.SPACE_XXS),
                                    on_click=lambda e: (
                                        on_clear_output() if on_clear_output else None
                                    ),
                                ),
                            ],
                            spacing=tokens.SPACE_NONE,
                        ),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                ),
            ],
            spacing=tokens.SPACE_XXS,
        ),
        padding=ft.Padding(
            tokens.SPACE_SM, tokens.SPACE_XS, tokens.SPACE_SM, tokens.SPACE_XS
        ),
        bgcolor=theme.TERMINAL_BG,
        border_radius=tokens.RADIUS_SM,
        visible=bool(output_controls) or is_running,
        width=float("inf"),
    )

    play_button = ft.IconButton(
        ft.Icons.PLAY_ARROW_ROUNDED,
        ref=play_btn_ref,
        icon_size=tokens.ICON_MD,
        icon_color=theme.SUCCESS,
        on_click=lambda e: on_run() if on_run else None,
        tooltip="Run Cell",
        style=ft.ButtonStyle(padding=tokens.SPACE_XS),
        visible=not is_running,
    )

    stop_row = ft.Row(
        ref=stop_row_ref,
        controls=[
            ft.ProgressRing(
                width=tokens.PROGRESS_RING_XS,
                height=tokens.PROGRESS_RING_XS,
                stroke_width=tokens.PROGRESS_RING_STROKE_THIN,
            ),
            ft.IconButton(
                ft.Icons.STOP_ROUNDED,
                icon_size=tokens.ICON_XS,
                icon_color=theme.ERROR,
                on_click=lambda e: on_stop() if on_stop else None,
                tooltip="Stop",
                style=ft.ButtonStyle(padding=tokens.SPACE_XXS),
            ),
        ],
        spacing=tokens.SPACE_XS,
        visible=is_running,
    )

    # Compact code editor
    editor = ft.TextField(
        ref=editor_ref,
        value=source,
        multiline=True,
        min_lines=1,
        max_lines=12,
        text_style=ft.TextStyle(font_family="RobotoMono", size=tokens.FONT_SM),
        border_color=ft.Colors.TRANSPARENT,
        bgcolor=ft.Colors.TRANSPARENT,
        on_change=_handle_change,
        hint_text="# Write Python code…",
        content_padding=ft.Padding(
            tokens.SPACE_SM,
            tokens.SPACE_XS,
            tokens.SPACE_SM,
            tokens.SPACE_XS,
        ),
        expand=True,
    )

    # Toolbar row: play/stop + spacer + actions
    toolbar = ft.Container(
        content=ft.Row(
            controls=[
                play_button,
                stop_row,
                ft.Container(expand=True),
                _make_actions(),
            ],
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        padding=ft.Padding(
            tokens.SPACE_XS,
            tokens.SPACE_NONE,
            tokens.SPACE_SM,
            tokens.SPACE_XS,
        ),
    )

    code_box = ft.Container(
        content=ft.Column(
            controls=[editor, toolbar],
            spacing=tokens.SPACE_NONE,
        ),
        border_radius=tokens.RADIUS_SM,
        bgcolor=ft.Colors.with_opacity(tokens.OPACITY_SUBTLE, ft.Colors.ON_SURFACE),
    )

    content = ft.Column(
        controls=[
            code_box,
            ft.Container(
                content=output_panel,
                padding=ft.Padding(
                    tokens.SPACE_NONE,
                    tokens.SPACE_XXS,
                    tokens.SPACE_NONE,
                    tokens.SPACE_NONE,
                ),
            ),
        ],
        spacing=tokens.SPACE_NONE,
    )

    container = ft.Container(
        content=content,
        padding=ft.Padding(
            tokens.SPACE_SM, tokens.SPACE_XS, tokens.SPACE_SM, tokens.SPACE_XS
        ),
        border=ft.Border(
            left=ft.BorderSide(
                tokens.SPACE_NANO,
                ft.Colors.with_opacity(tokens.OPACITY_BORDER, ft.Colors.ON_SURFACE),
            ),
        ),
        margin=ft.Margin(
            tokens.SPACE_NONE, tokens.SPACE_XXS, tokens.SPACE_NONE, tokens.SPACE_XXS
        ),
    )

    return container, refs
