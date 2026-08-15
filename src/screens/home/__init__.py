"""HomeScreen — Modular dashboard with Colab session status, quick actions, and features."""

from __future__ import annotations

import logging

import flet as ft

from components.brand_header import build_brand_header
from core import theme, tokens
from core.utils import get_banner_ad
from screens.home.cards import (
    action_card,
    build_recent_projects_section,
    feature_card,
    step_row,
)
from screens.home.status_banner import build_colab_status_bar
from state import AppStateCtx
from state.controller_ctx import ControllerMethodsCtx
from state.service_ctx import ServiceCtx

logger = logging.getLogger("HomeScreen")


@ft.component
def HomeScreen() -> ft.Control:
    """Build the Home landing screen assembling modular cards and quick actions."""
    state = ft.use_context(AppStateCtx)
    services = ft.use_context(ServiceCtx)
    controller = ft.use_context(ControllerMethodsCtx)
    page = ft.context.page

    projects, set_projects = ft.use_state([])

    # ── Load projects ───────────────────────────────────────────
    async def _load_projects_effect():
        if services.projects:
            try:
                loaded = await services.projects.list_projects()
                set_projects(loaded)
                state.projects_list = loaded
            except Exception as err:
                logger.warning("Failed to load projects list: %s", err)

    ft.use_effect(_load_projects_effect, [state.active_project_id])

    async def _on_open_project(p: dict):
        if services.projects:
            full_proj = await services.projects.get_project(p["id"])
            if full_proj:
                state.load_project(full_proj)
                controller.navigate_tab(1)

    async def _on_create_new_project(_=None):
        if services.projects:
            existing = await services.projects.list_projects()
            name = f"Project {len(existing) + 1}"
            new_p = await services.projects.create_project(name=name)
            state.load_project(new_p)
            controller.navigate_tab(1)

    def _show_delete_dialog(p: dict):
        pname = p.get("name", "Untitled Project")
        pid = p.get("id", "")

        def _confirm_delete(_):
            async def _delete_task():
                page.pop_dialog()
                try:
                    if services.projects:
                        await services.projects.delete_project(pid)
                    if state.active_project_id == pid:
                        existing = await services.projects.list_projects()
                        if existing:
                            full = await services.projects.get_project(
                                existing[0]["id"]
                            )
                            if full:
                                state.load_project(full)
                        else:
                            new_p = await services.projects.create_project(
                                name="Project 1"
                            )
                            state.load_project(new_p)
                    await _load_projects_effect()
                    page.snack_bar = ft.SnackBar(
                        ft.Text(f"🗑️ Project '{pname}' deleted")
                    )
                    page.snack_bar.open = True
                    page.update()
                except Exception as ex:
                    logger.error("Delete project failed: %s", ex)

            page.run_task(_delete_task)

        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Row(
                [
                    ft.Icon(ft.Icons.DELETE_FOREVER_ROUNDED, color=theme.ERROR),
                    ft.Text("Delete Project", weight=ft.FontWeight.BOLD),
                ],
                spacing=tokens.SPACE_XS,
            ),
            content=ft.Text(
                f"Are you sure you want to delete '{pname}'?\n"
                "All notebook cells and local cache for this project will be permanently removed.",
                size=tokens.FONT_SM,
            ),
            actions=[
                ft.TextButton("Cancel", on_click=lambda _: page.pop_dialog()),
                ft.FilledButton(
                    "Delete",
                    style=ft.ButtonStyle(
                        bgcolor=theme.ERROR,
                        color=ft.Colors.WHITE,
                    ),
                    on_click=_confirm_delete,
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        page.show_dialog(dialog)

    async def _on_quick_start_analysis(autopilot: bool = False):
        if services.projects:
            existing = await services.projects.list_projects()
            name = f"Project {len(existing) + 1}"
            new_p = await services.projects.create_project(name=name)
            state.load_project(new_p)
        else:
            state.clear_notebook()
        controller.start_analysis(autopilot=autopilot)

    # ── Quick actions ───────────────────────────────────────────
    quick_actions = ft.Container(
        content=ft.Column(
            controls=[
                ft.Text(
                    "Quick Start",
                    size=tokens.FONT_MD,
                    weight=ft.FontWeight.W_600,
                ),
                ft.Container(height=tokens.SPACE_SM),
                ft.Row(
                    controls=[
                        action_card(
                            icon=ft.Icons.AUTO_AWESOME_ROUNDED,
                            title="Analyze Data",
                            subtitle="AI + Colab",
                            color=theme.PRIMARY,
                            on_click=lambda _: (
                                page.run_task(_on_quick_start_analysis, False)
                                if page
                                else controller.start_analysis(autopilot=False)
                            ),
                        ),
                        action_card(
                            icon=ft.Icons.ROCKET_LAUNCH_ROUNDED,
                            title="Autopilot",
                            subtitle="Auto-report",
                            color=theme.ACCENT,
                            on_click=lambda _: (
                                page.run_task(_on_quick_start_analysis, True)
                                if page
                                else controller.start_analysis(autopilot=True)
                            ),
                        ),
                    ],
                    spacing=tokens.SPACE_MD,
                ),
                ft.Container(height=tokens.SPACE_SM),
                ft.Row(
                    controls=[
                        action_card(
                            icon=ft.Icons.DYNAMIC_FORM_ROUNDED,
                            title="Surveys",
                            subtitle="AI forms",
                            color=theme.WARNING,
                            on_click=lambda e: controller.navigate_tab(2),
                        ),
                        action_card(
                            icon=ft.Icons.ASSESSMENT_ROUNDED,
                            title="Reports",
                            subtitle=f"{len(state.user_reports or [])} saved",
                            color=theme.SUCCESS,
                            on_click=lambda e: controller.navigate_tab(3),
                        ),
                    ],
                    spacing=tokens.SPACE_MD,
                ),
            ],
            spacing=0,
        ),
        padding=ft.Padding(tokens.SPACE_LG, 0, tokens.SPACE_LG, tokens.SPACE_LG),
    )

    # ── Cloud power banner ──────────────────────────────────────
    cloud_banner = ft.Container(
        content=ft.Row(
            controls=[
                ft.Icon(
                    ft.Icons.MEMORY_ROUNDED, size=tokens.ICON_MD, color=theme.PRIMARY
                ),
                ft.Column(
                    controls=[
                        ft.Text(
                            "Colab-Powered Analysis",
                            size=tokens.FONT_SM,
                            weight=ft.FontWeight.W_600,
                        ),
                        ft.Text(
                            "Your data runs on Google Colab's GPU/TPU VMs. "
                            "No local limits — use pandas, scikit-learn, "
                            "TensorFlow, and more.",
                            size=tokens.FONT_XS,
                            color=ft.Colors.ON_SURFACE_VARIANT,
                        ),
                    ],
                    spacing=tokens.SPACE_XXS,
                    expand=True,
                ),
            ],
            spacing=tokens.SPACE_MD,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        padding=ft.Padding(
            tokens.SPACE_LG, tokens.SPACE_MD, tokens.SPACE_LG, tokens.SPACE_MD
        ),
        margin=ft.Margin(
            tokens.SPACE_LG, tokens.SPACE_SM, tokens.SPACE_LG, tokens.SPACE_SM
        ),
        border_radius=tokens.RADIUS_LG,
        bgcolor=ft.Colors.with_opacity(0.06, theme.PRIMARY),
        border=ft.Border.all(1, ft.Colors.with_opacity(0.15, theme.PRIMARY)),
    )

    # ── Features ────────────────────────────────────────────────
    features = ft.Container(
        content=ft.Column(
            controls=[
                ft.Text(
                    "What SpanInsight Does",
                    size=tokens.FONT_MD,
                    weight=ft.FontWeight.W_600,
                ),
                ft.Container(height=tokens.SPACE_SM),
                feature_card(
                    ft.Icons.AUTO_AWESOME_ROUNDED,
                    "AI-Powered Analysis",
                    "Upload any dataset. AI writes Python code and runs it on "
                    "Colab — generating charts, ML models, and statistical insights.",
                    theme.PRIMARY,
                ),
                feature_card(
                    ft.Icons.DYNAMIC_FORM_ROUNDED,
                    "Smart Surveys",
                    "Describe a questionnaire in plain English. AI generates it. "
                    "Share a link, collect responses, and analyze results.",
                    theme.WARNING,
                ),
                feature_card(
                    ft.Icons.ROCKET_LAUNCH_ROUNDED,
                    "Autopilot Mode",
                    "One tap. AI runs multiple analysis passes on Colab, "
                    "generates charts, and builds a complete report.",
                    theme.ACCENT,
                ),
                feature_card(
                    ft.Icons.CODE_ROUNDED,
                    "Expert Code Mode",
                    "Toggle to code mode and write Python directly. "
                    "Full Colab runtime at your fingertips — install any package.",
                    theme.SUCCESS,
                ),
            ],
            spacing=tokens.SPACE_MD,
        ),
        padding=ft.Padding(
            tokens.SPACE_LG, tokens.SPACE_LG, tokens.SPACE_LG, tokens.SPACE_SM
        ),
    )

    # ── How it works ────────────────────────────────────────────
    how_it_works = ft.Container(
        content=ft.Column(
            controls=[
                ft.Text(
                    "How It Works",
                    size=tokens.FONT_MD,
                    weight=ft.FontWeight.W_600,
                ),
                ft.Container(height=tokens.SPACE_SM),
                step_row("1", "Connect", "Sign in to Google Colab in one tap"),
                step_row("2", "Upload", "Send your data file to Colab's cloud VM"),
                step_row("3", "Analyze", "Ask questions or let Autopilot run"),
                step_row("4", "Export", "Save as .ipynb or share via Google Drive"),
            ],
            spacing=tokens.SPACE_MD,
        ),
        padding=ft.Padding(
            tokens.SPACE_LG, tokens.SPACE_LG, tokens.SPACE_LG, tokens.SPACE_SM
        ),
    )

    # ── Credits info ────────────────────────────────────────────
    credits_info = ft.Container(
        content=ft.Row(
            controls=[
                ft.Icon(ft.Icons.BOLT_ROUNDED, size=20, color=theme.ACCENT),
                ft.Column(
                    [
                        ft.Text(
                            "50 Free Credits Daily",
                            size=tokens.FONT_SM,
                            weight=ft.FontWeight.W_600,
                        ),
                        ft.Text(
                            "Each AI analysis costs 1 credit. Resets at midnight UTC.",
                            size=tokens.FONT_XS,
                            color=ft.Colors.ON_SURFACE_VARIANT,
                        ),
                    ],
                    spacing=2,
                    expand=True,
                ),
            ],
            spacing=tokens.SPACE_MD,
            vertical_alignment="center",
        ),
        padding=ft.Padding(
            tokens.SPACE_LG, tokens.SPACE_MD, tokens.SPACE_LG, tokens.SPACE_MD
        ),
        margin=ft.Margin(tokens.SPACE_LG, 0, tokens.SPACE_LG, tokens.SPACE_LG),
        border_radius=tokens.RADIUS_LG,
        bgcolor=ft.Colors.with_opacity(0.06, theme.ACCENT),
        border=ft.Border.all(1, ft.Colors.with_opacity(0.15, theme.ACCENT)),
    )

    # ── Ad helper ───────────────────────────────────────────────
    def _create_home_ad() -> ft.Control:
        if page and page.platform in (ft.PagePlatform.ANDROID, ft.PagePlatform.IOS):
            try:
                return ft.Container(
                    content=ft.Column(
                        [
                            ft.Text(
                                "SPONSORED",
                                size=8,
                                weight=ft.FontWeight.W_700,
                                color=ft.Colors.ON_SURFACE_VARIANT,
                                style=ft.TextStyle(letter_spacing=1),
                            ),
                            get_banner_ad(),
                        ],
                        horizontal_alignment="center",
                        spacing=4,
                    ),
                    alignment=ft.Alignment.CENTER,
                    padding=8,
                    border_radius=tokens.RADIUS_LG,
                    bgcolor=theme.GLASS_BG,
                    border=ft.Border.all(1, theme.GLASS_BORDER_COLOR),
                    margin=ft.Margin(
                        tokens.SPACE_LG, 0, tokens.SPACE_LG, tokens.SPACE_LG
                    ),
                )
            except Exception:
                pass
        return ft.Container()

    # ── Assemble layout ─────────────────────────────────────────
    return ft.Column(
        controls=[
            build_colab_status_bar(state),
            build_brand_header(show_tagline=True, spacing_below=True),
            quick_actions,
            build_recent_projects_section(
                projects,
                on_open=lambda p: page.run_task(_on_open_project, p) if page else None,
                on_create_new=lambda _: (
                    page.run_task(_on_create_new_project) if page else None
                ),
                on_delete=_show_delete_dialog,
                on_view_all=lambda _: controller.open_projects_screen(),
            ),
            _create_home_ad(),
            cloud_banner,
            features,
            _create_home_ad(),
            how_it_works,
            credits_info,
            ft.Container(height=80),
        ],
        scroll=ft.ScrollMode.AUTO,
        expand=True,
        spacing=0,
    )
