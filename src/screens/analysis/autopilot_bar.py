"""Autopilot progress bar component for Analysis screen (consolidated into AgentProgressPill)."""

from __future__ import annotations

import flet as ft

from components.agent_progress_pill import build_agent_progress_pill


def build_autopilot_bar(
    is_running: bool,
    progress_text: str,
    on_stop,
) -> ft.Control:
    """Status bar showing active multi-step autopilot progress with a stop action."""
    return build_agent_progress_pill(
        is_active=is_running,
        is_autopilot=True,
        stage_text=progress_text,
        on_stop=on_stop,
    )
