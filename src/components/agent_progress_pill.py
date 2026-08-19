"""AgentProgressPill - unified expandable AI agent progress indicator & Autopilot controller."""

from __future__ import annotations

from collections.abc import Callable

import flet as ft

from core import theme, tokens


def build_agent_progress_pill(
    is_active: bool,
    is_autopilot: bool = False,
    stage_text: str = "",
    duration: float = 0.0,
    steps: list[dict] | None = None,
    on_stop: Callable | None = None,
    is_expanded: bool = False,
    on_toggle: Callable | None = None,
) -> ft.Container:
    """Unified AI Agent Progress Pill with live timeline drawer and Autopilot control."""
    if not is_active:
        return ft.Container(visible=False)

    from core.state import state

    current_stage = getattr(state, "analysis_stage", 2)
    display_stage = (
        state.analysis_stage_text
        or stage_text
        or (state.autopilot_progress if is_autopilot else "")
        or (
            "Inspecting dataset schema & context…"
            if current_stage == 1
            else "Reasoning & formulating analysis…"
            if current_stage == 2
            else "Synthesizing specialized Python code…"
            if current_stage == 3
            else "Executing in Colab kernel…"
            if current_stage == 4
            else "Compiling executive summary & takeaways…"
            if current_stage == 5
            else "🩹 AI self-healing execution error…"
            if current_stage == 6
            else "AI Agent working…"
        )
    )
    duration_str = f" ({duration:.1f}s)" if duration > 0 else ""

    # Build steps if not explicitly provided
    resolved_steps = steps or getattr(state, "autopilot_steps", None)
    if not resolved_steps:
        if is_autopilot:
            resolved_steps = [
                {"text": "Dataset distribution & overview", "status": "done"},
                {"text": "Correlation & driver analysis", "status": "running"},
                {"text": "Anomaly & pattern detection", "status": "pending"},
                {"text": "Statistical synthesis & summary", "status": "pending"},
            ]
        else:
            s1 = (
                "done"
                if current_stage >= 2
                else "running"
                if current_stage == 1
                else "pending"
            )
            s2 = (
                "done"
                if current_stage >= 3
                else "running"
                if current_stage == 2
                else "pending"
            )
            s3 = (
                "done"
                if current_stage >= 4
                else "running"
                if current_stage == 3
                else "pending"
            )
            s4 = (
                "done"
                if current_stage >= 5
                else "running"
                if current_stage in (4, 6)
                else "pending"
            )
            s5 = (
                "done"
                if current_stage == 0
                else "running"
                if current_stage == 5
                else "pending"
            )

            resolved_steps = [
                {"text": "Inspect dataset schema & context", "status": s1},
                {"text": "Deep AI reasoning & query formulation", "status": s2},
                {"text": "Synthesize specialized Python analysis", "status": s3},
                {
                    "text": "Execute in Colab kernel & render visuals",
                    "status": "running" if current_stage == 6 else s4,
                },
                {"text": "Executive takeaways & insights", "status": s5},
            ]
            if current_stage == 6:
                resolved_steps.insert(
                    4,
                    {"text": "🩹 AI self-healing execution error", "status": "running"},
                )

    # Render timeline step rows
    step_rows = []
    for s in resolved_steps:
        stype = s.get("status", "pending")
        icon = (
            ft.Icons.CHECK_CIRCLE_ROUNDED
            if stype == "done"
            else ft.Icons.RADIO_BUTTON_CHECKED_ROUNDED
            if stype == "running"
            else ft.Icons.RADIO_BUTTON_UNCHECKED_ROUNDED
        )
        icon_color = (
            theme.SUCCESS
            if stype == "done"
            else theme.PRIMARY
            if stype == "running"
            else ft.Colors.ON_SURFACE_VARIANT
        )

        step_rows.append(
            ft.Row(
                [
                    ft.Icon(icon, size=tokens.ICON_MICRO, color=icon_color),
                    ft.Text(
                        s.get("text", ""),
                        size=tokens.FONT_XXS,
                        color=ft.Colors.ON_SURFACE
                        if stype != "pending"
                        else ft.Colors.ON_SURFACE_VARIANT,
                        weight=ft.FontWeight.W_500
                        if stype == "running"
                        else ft.FontWeight.NORMAL,
                        expand=True,
                    ),
                    ft.Text(
                        s.get("time", ""),
                        size=tokens.FONT_XXS,
                        color=ft.Colors.ON_SURFACE_VARIANT,
                    ),
                ],
                spacing=tokens.SPACE_XS,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            )
        )

    drawer_controls = [ft.Column(step_rows, spacing=tokens.SPACE_XXS)]
    if is_autopilot:
        from core.utils import get_banner_ad

        drawer_controls.append(
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
                        get_banner_ad(),
                    ],
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=tokens.SPACE_TINY,
                ),
                alignment=ft.Alignment.CENTER,
                padding=tokens.SPACE_XS,
                margin=ft.Margin(
                    tokens.SPACE_NONE,
                    tokens.SPACE_XS,
                    tokens.SPACE_NONE,
                    tokens.SPACE_NONE,
                ),
            )
        )

    timeline_drawer = ft.Container(
        content=ft.Column(drawer_controls, spacing=tokens.SPACE_XS),
        padding=tokens.SPACE_SM,
        bgcolor=ft.Colors.with_opacity(tokens.OPACITY_CONTAINER, ft.Colors.BLACK),
        border_radius=tokens.RADIUS_SM,
        border=ft.Border.all(
            tokens.DIVIDER_THICKNESS,
            ft.Colors.with_opacity(tokens.OPACITY_BORDER, theme.PRIMARY),
        ),
        visible=is_expanded,
    )

    chevron_ref = ft.Ref[ft.IconButton]()

    def _handle_toggle(e=None):
        if on_toggle:
            on_toggle()
        else:
            # Fallback for standalone/testing contexts without parent reactive hook
            if hasattr(timeline_drawer, "_frozen"):
                try:
                    del timeline_drawer._frozen
                except AttributeError:
                    pass
            timeline_drawer.visible = not timeline_drawer.visible
            if chevron_ref.current:
                if hasattr(chevron_ref.current, "_frozen"):
                    try:
                        del chevron_ref.current._frozen
                    except AttributeError:
                        pass
                chevron_ref.current.icon = (
                    ft.Icons.KEYBOARD_ARROW_UP_ROUNDED
                    if timeline_drawer.visible
                    else ft.Icons.KEYBOARD_ARROW_DOWN_ROUNDED
                )
                try:
                    chevron_ref.current.update()
                except Exception:
                    pass
            try:
                timeline_drawer.update()
            except Exception:
                pass

    # Left controls: Spinner + Badge + Text
    left_controls = [
        ft.ProgressRing(
            width=tokens.PROGRESS_RING_XS,
            height=tokens.PROGRESS_RING_XS,
            stroke_width=tokens.PROGRESS_RING_STROKE_THIN,
            color=theme.PRIMARY,
        ),
    ]

    if is_autopilot:
        left_controls.append(
            ft.Container(
                content=ft.Row(
                    [
                        ft.Icon(
                            ft.Icons.AUTO_AWESOME_ROUNDED,
                            size=tokens.ICON_MICRO,
                            color=theme.PRIMARY,
                        ),
                        ft.Text(
                            "Autopilot",
                            size=tokens.FONT_XXS,
                            weight=ft.FontWeight.BOLD,
                            color=theme.PRIMARY,
                        ),
                    ],
                    spacing=tokens.SPACE_TINY,
                    tight=True,
                ),
                padding=ft.Padding(
                    tokens.SPACE_XS,
                    tokens.SPACE_TINY,
                    tokens.SPACE_XS,
                    tokens.SPACE_TINY,
                ),
                border_radius=tokens.RADIUS_XS,
                bgcolor=ft.Colors.with_opacity(tokens.OPACITY_MUTED, theme.PRIMARY),
            )
        )

    left_controls.append(
        ft.Text(
            f"{display_stage}{duration_str}",
            size=tokens.FONT_XS,
            weight=ft.FontWeight.W_500,
            color=ft.Colors.ON_SURFACE,
            no_wrap=True,
            overflow=ft.TextOverflow.ELLIPSIS,
            expand=True,
        )
    )

    # Right controls: Stop button (if Autopilot) + Expand toggle
    right_controls = []
    if is_autopilot and on_stop:
        right_controls.append(
            ft.TextButton(
                "Stop",
                on_click=on_stop,
                style=ft.ButtonStyle(
                    color=theme.ERROR,
                    padding=ft.Padding(
                        tokens.SPACE_SM,
                        tokens.SPACE_TINY,
                        tokens.SPACE_SM,
                        tokens.SPACE_TINY,
                    ),
                ),
            )
        )

    chevron_icon = (
        ft.Icons.KEYBOARD_ARROW_UP_ROUNDED
        if is_expanded
        else ft.Icons.KEYBOARD_ARROW_DOWN_ROUNDED
    )

    right_controls.append(
        ft.IconButton(
            ref=chevron_ref,
            icon=chevron_icon,
            icon_size=tokens.ICON_SM,
            icon_color=ft.Colors.ON_SURFACE_VARIANT,
            style=ft.ButtonStyle(padding=tokens.SPACE_NONE),
            tooltip="Toggle timeline drawer",
            on_click=_handle_toggle,
        )
    )

    header_content = ft.Row(
        controls=[
            ft.Row(
                left_controls,
                spacing=tokens.SPACE_SM,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                expand=True,
            ),
            ft.Row(
                right_controls,
                spacing=tokens.SPACE_XXS,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
        ],
        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
    )

    pill_container = ft.Container(
        content=header_content,
        height=tokens.BUTTON_HEIGHT_SM,
        padding=ft.Padding(
            tokens.SPACE_SM, tokens.SPACE_NONE, tokens.SPACE_XS, tokens.SPACE_NONE
        ),
        bgcolor=ft.Colors.with_opacity(tokens.OPACITY_MUTED, theme.PRIMARY),
        border_radius=tokens.RADIUS_SM,
        border=ft.Border.all(
            tokens.DIVIDER_THICKNESS,
            ft.Colors.with_opacity(tokens.OPACITY_BORDER, theme.PRIMARY),
        ),
        margin=ft.Margin(
            tokens.SPACE_NONE, tokens.SPACE_XXS, tokens.SPACE_NONE, tokens.SPACE_XXS
        ),
        on_click=_handle_toggle,
    )

    return ft.Container(
        content=ft.Column(
            [
                pill_container,
                timeline_drawer,
            ],
            spacing=tokens.SPACE_XXS,
        )
    )


# Backward-compatible alias
AgentProgressPill = build_agent_progress_pill
