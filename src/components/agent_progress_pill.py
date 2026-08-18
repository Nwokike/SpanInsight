"""AgentProgressPill — compact 32px live AI agent progress indicator with timeline drawer."""

from __future__ import annotations

import flet as ft

from core import theme, tokens


@ft.component
def AgentProgressPill(
    is_active: bool,
    stage_text: str = "",
    duration: float = 0.0,
    steps: list[dict] | None = None,
) -> ft.Control:
    """Renders a compact, non-intrusive 32px live AI agent progress pill with expandable timeline."""
    if not is_active:
        return ft.Container(visible=False)

    is_expanded, set_is_expanded = ft.use_state(False)

    from core.state import state

    current_stage = getattr(state, "analysis_stage", 2)
    display_stage = (
        state.analysis_stage_text
        or stage_text
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

    if not steps:
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

        steps = [
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
            steps.insert(
                4,
                {"text": "🩹 AI self-healing execution error", "status": "running"},
            )

    # Render timeline steps
    step_rows = []
    for s in steps:
        stype = s.get("status", "done")
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
                    ft.Icon(icon, size=12, color=icon_color),
                    ft.Text(
                        s.get("text", ""),
                        size=tokens.FONT_XXS,
                        color=ft.Colors.ON_SURFACE
                        if stype != "pending"
                        else ft.Colors.ON_SURFACE_VARIANT,
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

    timeline_drawer = ft.Container(
        content=ft.Column(step_rows, spacing=tokens.SPACE_XXS),
        padding=tokens.SPACE_SM,
        bgcolor=ft.Colors.with_opacity(0.04, ft.Colors.BLACK),
        border_radius=tokens.RADIUS_SM,
        border=ft.Border.all(1, ft.Colors.with_opacity(0.1, ft.Colors.ON_SURFACE)),
        visible=is_expanded,
    )

    def _toggle(_):
        set_is_expanded(not is_expanded)

    header_content = ft.Row(
        controls=[
            ft.Row(
                [
                    ft.ProgressRing(
                        width=14,
                        height=14,
                        stroke_width=2,
                        color=theme.PRIMARY,
                    ),
                    ft.Text(
                        f"{display_stage}{duration_str}",
                        size=tokens.FONT_XS,
                        weight=ft.FontWeight.W_500,
                        color=ft.Colors.ON_SURFACE,
                    ),
                ],
                spacing=tokens.SPACE_XS,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            ft.IconButton(
                icon=ft.Icons.KEYBOARD_ARROW_UP_ROUNDED
                if is_expanded
                else ft.Icons.KEYBOARD_ARROW_DOWN_ROUNDED,
                icon_size=16,
                icon_color=ft.Colors.ON_SURFACE_VARIANT,
                style=ft.ButtonStyle(padding=0),
                tooltip="Toggle timeline",
                on_click=_toggle,
            ),
        ],
        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
    )

    pill_container = ft.Container(
        content=header_content,
        height=32,
        padding=ft.Padding(tokens.SPACE_SM, 0, tokens.SPACE_XS, 0),
        bgcolor=ft.Colors.with_opacity(0.08, theme.PRIMARY),
        border_radius=tokens.RADIUS_SM,
        border=ft.Border.all(1, ft.Colors.with_opacity(0.2, theme.PRIMARY)),
        margin=ft.Margin(0, tokens.SPACE_XXS, 0, tokens.SPACE_XXS),
        on_click=_toggle,
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


def build_agent_progress_pill(
    is_active: bool,
    stage_text: str = "",
    duration: float = 0.0,
    steps: list[dict] | None = None,
    is_expanded: bool = False,
    on_toggle_expand=None,
) -> ft.Control:
    return AgentProgressPill(
        is_active=is_active,
        stage_text=stage_text,
        duration=duration,
        steps=steps,
    )
