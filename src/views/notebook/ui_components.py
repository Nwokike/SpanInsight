"""Notebook view UI components — evolved from v1 analysis view.

Keeps the proven patterns:
- Terminal widget with macOS dots header (View Code toggle)
- Block cards with collapsible code and output
- Skeleton loader for loading state

Removes pandas/numpy dependencies — outputs come as Colab dicts.
"""

import logging

import flet as ft

from components.notebook_cell.output import parse_outputs_to_controls
from core import theme, tokens
from core.state import state

logger = logging.getLogger(__name__)


def build_terminal(
    view_state,
    code: str,
    *,
    field_ref=None,
    on_run=None,
    filename="notebook.py",
) -> ft.Container:
    """Code editor with macOS-style terminal header.

    Evolved from v1 — same visual design, but runs code on Colab.
    """
    internal_field = ft.Ref[ft.TextField]()
    active_field = field_ref or internal_field

    def _on_run(e):
        if on_run and active_field.current:
            on_run(active_field.current.value.strip())

    show_run = on_run is not None

    return ft.Container(
        content=ft.Column(
            [
                # macOS dots header
                ft.Container(
                    content=ft.Row(
                        [
                            ft.Row(
                                [
                                    ft.Container(
                                        width=8,
                                        height=8,
                                        border_radius=4,
                                        bgcolor="#FF5F57",
                                    ),
                                    ft.Container(
                                        width=8,
                                        height=8,
                                        border_radius=4,
                                        bgcolor="#FEBC2E",
                                    ),
                                    ft.Container(
                                        width=8,
                                        height=8,
                                        border_radius=4,
                                        bgcolor="#28C840",
                                    ),
                                ],
                                spacing=4,
                            ),
                            ft.Text(filename, size=10, color="#888888"),
                            ft.TextButton(
                                "▶ Run",
                                icon=ft.Icons.PLAY_ARROW_ROUNDED,
                                style=ft.ButtonStyle(color="#28C840"),
                                disabled=state.is_analyzing,
                                on_click=_on_run,
                            )
                            if show_run
                            else ft.Container(),
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    ),
                    padding=ft.Padding(10, 6, 10, 6),
                    bgcolor=theme.TERMINAL_HEADER,
                    border_radius=ft.BorderRadius(
                        top_left=8, top_right=8, bottom_left=0, bottom_right=0
                    ),
                ),
                # Code editor
                ft.Container(
                    content=ft.TextField(
                        ref=active_field,
                        value=code,
                        multiline=True,
                        min_lines=3,
                        max_lines=20,
                        text_size=11,
                        text_style=ft.TextStyle(
                            font_family="RobotoMono", color="#E0E0E0"
                        ),
                        border_color=ft.Colors.TRANSPARENT,
                        bgcolor=ft.Colors.TRANSPARENT,
                        cursor_color="#28C840",
                        filled=False,
                    ),
                    padding=ft.Padding(12, 6, 12, 12),
                    bgcolor=theme.TERMINAL_BG,
                    border_radius=ft.BorderRadius(
                        top_left=0, top_right=0, bottom_left=8, bottom_right=8
                    ),
                ),
            ],
            spacing=0,
            horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
        ),
        margin=ft.Margin(0, 4, 0, 8),
    )


def build_output_panel(outputs: list) -> ft.Container | None:
    """Render Colab execution outputs (stream, error, images, text).

    Replaces v1's build_result_visualizer which depended on pandas/numpy.
    Outputs now come as Colab dicts:
    - {"type": "stream", "name": "stdout", "text": "..."}
    - {"type": "error", "traceback": [...], "ename": "...", "evalue": "..."}
    - {"type": "execute_result", "data": {"text/plain": "...", "image/png": "..."}}
    """
    output_controls = parse_outputs_to_controls(outputs)
    if not output_controls:
        return None

    # Dynamic height — compact for small outputs, scrollable for large
    line_count = 0
    for ctrl in output_controls:
        txt = getattr(ctrl, "value", "") or ""
        line_count += max(txt.count("\n") + 1, 1)
    calc_height = min(max(line_count * 18 + 12, 32), 280) if output_controls else None

    return ft.Container(
        content=ft.ListView(
            controls=output_controls,
            spacing=tokens.SPACE_XXS,
            auto_scroll=True,
            height=calc_height,
            expand=False,
        ),
        padding=ft.Padding(12, 8, 12, 8),
        bgcolor=theme.TERMINAL_BG,
        border_radius=8,
        border=ft.Border.all(1, theme.TERMINAL_HEADER),
    )


def build_block_card(view_state, block: dict, index: int) -> ft.Container:
    """Build a result block card — evolved from v1.

    Each block represents one AI analysis step:
    - Header: prompt/description with icon
    - Output: Colab execution output (text, images, errors)
    - Description: AI's insight text
    - Collapsible Code: View/edit/re-run the generated code
    - Action buttons: pin to report, retry, delete
    """
    is_failed = block.get("failed", False)
    controls: list[ft.Control] = []

    # ── Header ──────────────────────────────────────────────────
    header_color = theme.ERROR if is_failed else theme.ACCENT
    controls.append(
        ft.Row(
            [
                ft.Icon(
                    ft.Icons.ERROR_OUTLINE_ROUNDED
                    if is_failed
                    else ft.Icons.AUTO_AWESOME_ROUNDED,
                    size=14,
                    color=header_color,
                ),
                ft.Text(
                    block.get("prompt", ""),
                    weight="bold",
                    expand=True,
                    max_lines=2,
                    overflow="ellipsis",
                ),
            ],
            spacing=8,
        )
    )

    # ── Output (Colab results) ──────────────────────────────────
    outputs = block.get("outputs", [])
    if outputs:
        output_panel = build_output_panel(outputs)
        if output_panel:
            # Collapsible output toggle
            output_ref = ft.Ref[ft.Container]()

            def toggle_output(e, ref=output_ref):
                ref.current.visible = not ref.current.visible
                view_state.page.update()

            controls.append(
                ft.Container(
                    content=ft.Row(
                        [
                            ft.Icon(
                                ft.Icons.KEYBOARD_ARROW_DOWN_ROUNDED,
                                size=16,
                                color=ft.Colors.ON_SURFACE_VARIANT,
                            ),
                            ft.Text(
                                "View Output",
                                size=11,
                                color=ft.Colors.ON_SURFACE_VARIANT,
                            ),
                        ],
                        alignment="center",
                        spacing=4,
                    ),
                    on_click=toggle_output,
                    ink=True,
                    padding=ft.Padding(0, 2, 0, 0),
                    alignment=ft.Alignment.CENTER,
                )
            )
            controls.append(
                ft.Container(
                    ref=output_ref,
                    content=output_panel,
                    visible=True,  # Show output by default
                )
            )

    # ── Stdout (plain text fallback) ────────────────────────────
    stdout_val = block.get("stdout", "")
    if stdout_val and not outputs:
        controls.append(
            ft.Container(
                content=ft.Text(
                    str(stdout_val).strip(),
                    size=11,
                    font_family="RobotoMono",
                    color="#E0E0E0",
                ),
                padding=12,
                bgcolor=theme.TERMINAL_BG,
                border_radius=8,
            )
        )

    # ── Description / Insight ───────────────────────────────────
    desc = block.get("description", "")
    if desc:
        controls.append(
            ft.Container(
                content=ft.Row(
                    [
                        ft.Icon(
                            ft.Icons.LIGHTBULB_OUTLINE_ROUNDED,
                            size=14,
                            color=theme.ACCENT,
                        ),
                        ft.Text(
                            desc,
                            size=tokens.FONT_SM,
                            color=ft.Colors.ON_SURFACE_VARIANT,
                            expand=True,
                        ),
                    ],
                    vertical_alignment="start",
                ),
                padding=10,
                bgcolor=ft.Colors.with_opacity(0.05, theme.ACCENT),
                border_radius=8,
            )
        )

    # ── Collapsible Code ────────────────────────────────────────
    code = block.get("code", "")
    if code:
        adv = ft.Ref[ft.Container]()

        def toggle_code(e, ref=adv):
            ref.current.visible = not ref.current.visible
            view_state.page.update()

        controls.append(
            ft.Container(
                content=ft.Row(
                    [
                        ft.Icon(
                            ft.Icons.KEYBOARD_ARROW_DOWN_ROUNDED,
                            size=16,
                            color=ft.Colors.ON_SURFACE_VARIANT,
                        ),
                        ft.Text(
                            "View Code",
                            size=11,
                            color=ft.Colors.ON_SURFACE_VARIANT,
                        ),
                    ],
                    alignment="center",
                    spacing=4,
                ),
                on_click=toggle_code,
                ink=True,
                padding=ft.Padding(0, 2, 0, 0),
                alignment=ft.Alignment.CENTER,
            )
        )
        controls.append(
            ft.Container(
                ref=adv,
                content=build_terminal(
                    view_state,
                    code,
                    on_run=lambda c: view_state.page.run_task(
                        _rerun_on_colab, view_state, index, c
                    ),
                ),
                visible=False,
            )
        )

    # ── Action Buttons ──────────────────────────────────────────
    if not is_failed:
        action_row = []
        action_row.append(
            ft.TextButton(
                "Add to Report",
                icon=ft.Icons.BOOKMARK_ADD_ROUNDED,
                style=ft.ButtonStyle(
                    color=theme.ACCENT,
                    shape=ft.RoundedRectangleBorder(radius=8),
                ),
            )
        )
        action_row.append(
            ft.IconButton(
                ft.Icons.DELETE_OUTLINE_ROUNDED,
                icon_size=16,
                icon_color=ft.Colors.ON_SURFACE_VARIANT,
                tooltip="Remove block",
                on_click=lambda e, idx=index: _delete_block(view_state, idx),
            )
        )
        controls.append(
            ft.Row(action_row, alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
        )
    else:
        controls.append(
            ft.Row(
                [
                    ft.TextButton(
                        "Retry with AI",
                        icon=ft.Icons.REFRESH_ROUNDED,
                        style=ft.ButtonStyle(color=theme.ERROR),
                    ),
                    ft.IconButton(
                        ft.Icons.DELETE_OUTLINE_ROUNDED,
                        icon_size=16,
                        icon_color=ft.Colors.ON_SURFACE_VARIANT,
                        on_click=lambda e, idx=index: _delete_block(view_state, idx),
                    ),
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            )
        )

    return ft.Container(
        content=ft.Column(controls, spacing=8),
        padding=16,
        border_radius=12,
        bgcolor=ft.Colors.with_opacity(0.03, ft.Colors.ON_SURFACE),
        border=ft.Border.all(
            1,
            theme.ERROR
            if is_failed
            else ft.Colors.with_opacity(0.08, ft.Colors.ON_SURFACE),
        ),
        margin=ft.Margin(12, 4, 12, 4),
    )


def build_skeleton_loader() -> ft.Container:
    """Pulse skeleton card shown while AI/Colab is thinking."""
    return ft.Container(
        content=ft.Column(
            [
                ft.Container(
                    width=200,
                    height=14,
                    border_radius=4,
                    bgcolor=ft.Colors.with_opacity(0.08, ft.Colors.ON_SURFACE),
                ),
                ft.Container(height=6),
                ft.Container(
                    width=float("inf"),
                    height=60,
                    border_radius=8,
                    bgcolor=ft.Colors.with_opacity(0.05, ft.Colors.ON_SURFACE),
                ),
                ft.Container(height=4),
                ft.Container(
                    width=140,
                    height=12,
                    border_radius=4,
                    bgcolor=ft.Colors.with_opacity(0.06, ft.Colors.ON_SURFACE),
                ),
            ],
            spacing=4,
        ),
        padding=16,
        border_radius=12,
        bgcolor=ft.Colors.with_opacity(0.02, ft.Colors.ON_SURFACE),
        border=ft.Border.all(1, ft.Colors.with_opacity(0.06, ft.Colors.ON_SURFACE)),
        margin=ft.Margin(12, 4, 12, 4),
        animate_opacity=ft.Animation(800, ft.AnimationCurve.EASE_IN_OUT),
    )


def _delete_block(view_state, index: int):
    """Remove a block from the notebook."""
    if 0 <= index < len(state.notebook_cells):
        state.notebook_cells.pop(index)
        view_state.rebuild()


async def _rerun_on_colab(view_state, block_index: int, new_code: str):
    """Re-run edited code on Colab and update the block."""
    if not new_code.strip():
        return

    blocks = state.notebook_cells
    if block_index < 0 or block_index >= len(blocks):
        return

    block = blocks[block_index]
    block["code"] = new_code
    block["is_running"] = True
    view_state.rebuild()

    try:
        outputs = await view_state.colab_service.execute(
            code=new_code,
            session_name=state.active_session_name,
        )
        block["outputs"] = outputs
        block["failed"] = any(o.get("type") == "error" for o in outputs)
    except Exception as ex:
        block["outputs"] = [
            {
                "type": "error",
                "traceback": [str(ex)],
                "ename": "ExecutionError",
                "evalue": str(ex),
            }
        ]
        block["failed"] = True
    finally:
        block["is_running"] = False
        view_state.rebuild()
