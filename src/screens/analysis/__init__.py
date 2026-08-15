"""AnalysisScreen — Modular Colab notebook autopilot & AI Data Intelligence engine."""

from __future__ import annotations

import json
import logging

import flet as ft
from flet import Control

from components.dataset_overview_card import build_dataset_overview_card
from components.project_switcher import build_project_switcher
from components.suggestion_chips import build_suggestion_chips
from core import theme, tokens
from core.constants import STORAGE_NOTEBOOKS
from core.state import state
from screens.analysis.autopilot_bar import build_autopilot_bar
from screens.analysis.cell_list import build_add_cell_row, build_cells_container
from screens.analysis.empty_state import build_empty_state
from screens.analysis.fab_menu import build_analysis_fab
from screens.analysis.handlers import (
    connect_colab_async,
    export_ipynb_async,
    pick_and_upload_file_async,
    run_autopilot_async,
    run_cell_async,
    submit_prompt_async,
)
from screens.analysis.prompt_bar import build_gen_indicator, build_prompt_bar
from screens.analysis.session_banner import (
    build_session_banner,
    build_session_chip,
)
from screens.files.modal import show_manage_files_modal
from state import AppStateCtx
from state.controller_ctx import ControllerMethodsCtx
from state.service_ctx import ServiceCtx

logger = logging.getLogger("AnalysisScreen")


@ft.component
def AnalysisScreen() -> Control:
    """Analysis engine — AI prompt, dataset intelligence, notebook cells, autopilot."""
    services = ft.use_context(ServiceCtx)
    _controller = ft.use_context(ControllerMethodsCtx)
    app_state = ft.use_context(AppStateCtx)
    page = ft.context.page

    colab = services.colab
    storage = services.storage
    credits = services.credits
    projects = services.projects

    # ── Local state ──────────────────────────────────────────────
    prompt_text, set_prompt_text = ft.use_state("")
    _is_executing, set_is_executing = ft.use_state(False)
    is_connecting, set_is_connecting = ft.use_state(False)
    is_generating, set_is_generating = ft.use_state(False)
    is_recording, set_is_recording = ft.use_state(False)
    is_expert_mode, set_is_expert_mode = ft.use_state(False)
    suggestions, set_suggestions = ft.use_state([])
    suggestions_loading, set_suggestions_loading = ft.use_state(False)
    cells_version, set_cells_version = ft.use_state(0)
    schema_json, set_schema_json = ft.use_state({})

    # ── Refs ─────────────────────────────────────────────────────
    cell_refs_map = ft.use_ref({})
    prompt_ref = ft.Ref[ft.TextField]()

    session_name = app_state.active_session_name

    # ── Lifecycle: load/save notebook ───────────────────────────
    async def _on_mount():
        await _load_notebook()

    ft.use_effect(_on_mount, [state.active_project_id])

    async def _load_notebook():
        try:
            if projects and state.active_project_id:
                proj = await projects.get_project(state.active_project_id)
                if proj:
                    state.notebook_cells = list(proj.get("notebook_cells", []))
                    if proj.get("schema_json"):
                        set_schema_json(proj["schema_json"])
                    set_cells_version(cells_version + 1)
                    return
            if storage:
                raw = await storage.get(STORAGE_NOTEBOOKS)
                if raw:
                    data = json.loads(raw)
                    if isinstance(data, list) and data:
                        state.notebook_cells = data
                        set_cells_version(cells_version + 1)
        except Exception as e:
            logger.warning("Failed to load notebook: %s", e)

    async def _save_notebook():
        try:
            if storage:
                await storage.set(
                    STORAGE_NOTEBOOKS,
                    json.dumps(state.notebook_cells, default=str),
                )
            if projects and state.active_project_id:
                proj = await projects.get_project(state.active_project_id)
                if proj:
                    proj["notebook_cells"] = state.notebook_cells
                    proj["session_name"] = state.active_session_name
                    if schema_json:
                        proj["schema_json"] = schema_json
                    await projects.save_project(proj)
        except Exception as e:
            logger.warning("Failed to save notebook: %s", e)

    def _on_cell_change():
        set_cells_version(cells_version + 1)
        if page:
            page.run_task(_save_notebook)

    # ── Cell operations ──────────────────────────────────────────
    def _add_cell(cell_type: str = "code", source: str = ""):
        cell = state.add_cell(cell_type, source)
        _on_cell_change()
        return cell

    def _run_cell(cell_id: str):
        return run_cell_async(
            cell_id,
            session_name,
            colab,
            page,
            cell_refs_map,
            set_is_executing,
            _on_cell_change,
        )

    def _stop_cell(cell_id: str):
        cell = next((c for c in state.notebook_cells if c["id"] == cell_id), None)
        if cell:
            cell["is_running"] = False
            _on_cell_change()

    def _delete_cell(cell_id: str):
        state.notebook_cells = [c for c in state.notebook_cells if c["id"] != cell_id]
        _on_cell_change()

    def _move_cell(cell_id: str, direction: int):
        cells = state.notebook_cells
        idx = next((i for i, c in enumerate(cells) if c["id"] == cell_id), -1)
        if idx >= 0 and 0 <= idx + direction < len(cells):
            cells[idx], cells[idx + direction] = cells[idx + direction], cells[idx]
            state.notebook_cells = list(cells)
            _on_cell_change()

    def _clear_cell_output(cell_id: str):
        cell = next((c for c in state.notebook_cells if c["id"] == cell_id), None)
        if cell:
            cell["outputs"] = []
            _on_cell_change()

    def _pin_block_to_report(block: dict):
        block["pinned"] = not block.get("pinned", False)
        _on_cell_change()
        if page:
            page.snack_bar = ft.SnackBar(
                ft.Text(
                    "📌 Pinned to Reports!"
                    if block["pinned"]
                    else "Unpinned from Reports"
                )
            )
            page.snack_bar.open = True
            page.update()

    # ── Suggestions ──────────────────────────────────────────────
    async def _fetch_suggestions():
        if not schema_json:
            return
        set_suggestions_loading(True)
        try:
            from services.ai import analysis as ai_service

            ctx = "\n".join(
                c.get("source", "")[:80]
                for c in state.notebook_cells
                if c.get("type") == "code" and c.get("source")
            )
            result = await ai_service.suggest(schema_json, analysis_context=ctx)
            if result:
                set_suggestions(result)
        except Exception as e:
            logger.warning("Suggestions failed: %s", e)
        finally:
            set_suggestions_loading(False)

    ft.use_effect(_fetch_suggestions, [bool(schema_json)])

    # ── Prompt & File actions ────────────────────────────────────
    async def _submit_prompt(p: str):
        await submit_prompt_async(
            p,
            session_name,
            schema_json,
            credits,
            page,
            _add_cell,
            _run_cell,
            _fetch_suggestions,
            set_is_generating,
            set_prompt_text,
            _on_cell_change,
        )

    async def _pick_and_upload_file():
        await pick_and_upload_file_async(
            session_name,
            colab,
            page,
            _add_cell,
            _run_cell,
            _fetch_suggestions,
            set_schema_json,
            set_is_generating,
        )

    async def _toggle_voice():
        if is_recording:
            set_is_recording(False)
            try:
                from services.audio_service import stop_recording

                audio_bytes = await stop_recording()
                if audio_bytes:
                    from services.ai.client import transcribe_audio

                    text = await transcribe_audio(audio_bytes)
                    if text:
                        set_prompt_text(text)
            except Exception as ex:
                logger.warning("Voice processing error: %s", ex)
        else:
            set_is_recording(True)
            try:
                from services.audio_service import start_recording

                ok = await start_recording()
                if not ok:
                    set_is_recording(False)
                    if page:
                        page.snack_bar = ft.SnackBar(
                            ft.Text(
                                "Microphone unavailable on this platform. Please type your query."
                            )
                        )
                        page.snack_bar.open = True
                        page.update()
            except Exception as ex:
                set_is_recording(False)
                if page:
                    page.snack_bar = ft.SnackBar(
                        ft.Text(f"Voice recording not supported: {ex}")
                    )
                    page.snack_bar.open = True
                    page.update()

    # ── Floating Action Button ───────────────────────────────────
    def _sync_fab():
        if not page or not page.views:
            return

        def _cleanup():
            if page and page.views:
                try:
                    page.views[0].floating_action_button = None
                    page.update()
                except Exception:
                    pass

        if not session_name or state.autopilot_running:
            _cleanup()
            return

        has_schema = bool(schema_json)
        fab = build_analysis_fab(
            has_session=bool(session_name),
            has_cells=bool(state.notebook_cells),
            has_schema=has_schema,
            autopilot_running=state.autopilot_running,
            on_autopilot=lambda: page.run_task(
                run_autopilot_async,
                session_name,
                schema_json,
                credits,
                page,
                _add_cell,
                _run_cell,
            ),
            on_upload_dataset=lambda: page.run_task(_pick_and_upload_file),
            on_manage_files=lambda: show_manage_files_modal(page, colab, session_name),
            on_export_ipynb=lambda: page.run_task(export_ipynb_async, page),
        )

        try:
            page.views[0].floating_action_button = fab
            page.update()
        except Exception:
            pass

        return _cleanup

    ft.use_effect(
        _sync_fab,
        [session_name, cells_version, bool(schema_json), state.autopilot_running],
    )

    # ── No Session Guard ─────────────────────────────────────────
    if not session_name:
        return ft.SafeArea(
            content=build_session_banner(
                on_connect=lambda _: page.run_task(
                    connect_colab_async, colab, page, set_is_connecting
                ),
                is_connecting=is_connecting,
            ),
            expand=True,
        )

    # ── UI Construction ──────────────────────────────────────────
    session_chip = build_session_chip(session_name, state.session_hardware)
    autopilot_bar = build_autopilot_bar(
        is_running=state.autopilot_running,
        progress_text=state.autopilot_progress,
        on_stop=lambda _: setattr(state, "autopilot_cancelled", True),
    )

    mode_toggle_btn = ft.Container(
        content=ft.Row(
            [
                ft.Icon(
                    ft.Icons.AUTO_AWESOME_ROUNDED
                    if not is_expert_mode
                    else ft.Icons.TERMINAL_ROUNDED,
                    size=14,
                    color=theme.ACCENT if not is_expert_mode else theme.PRIMARY,
                ),
                ft.Text(
                    "Insight View" if not is_expert_mode else "Expert Mode",
                    size=tokens.FONT_XS,
                    weight=ft.FontWeight.W_600,
                    color=theme.ACCENT if not is_expert_mode else theme.PRIMARY,
                ),
            ],
            spacing=tokens.SPACE_XXS,
        ),
        padding=ft.Padding(
            tokens.SPACE_SM, tokens.SPACE_XXS, tokens.SPACE_SM, tokens.SPACE_XXS
        ),
        border_radius=tokens.RADIUS_SM,
        bgcolor=ft.Colors.with_opacity(
            0.1, theme.ACCENT if not is_expert_mode else theme.PRIMARY
        ),
        tooltip="Toggle between SpanInsight Insight Cards and Expert Notebook Cells",
        on_click=lambda _: set_is_expert_mode(not is_expert_mode),
    )

    project_chip = build_project_switcher(
        page,
        projects,
        on_project_selected=lambda p: set_cells_version(cells_version + 1),
    )

    top_bar = ft.Column(
        controls=[
            ft.Container(
                content=ft.Row(
                    controls=[
                        project_chip,
                        ft.Row(
                            [mode_toggle_btn, session_chip],
                            spacing=tokens.SPACE_XS,
                        ),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                padding=ft.Padding(
                    tokens.SPACE_MD, tokens.SPACE_SM, tokens.SPACE_MD, 0
                ),
            ),
            autopilot_bar,
        ],
        spacing=0,
    )

    # ── Feed Construction ────────────────────────────────────────
    cell_controls = build_cells_container(
        page=page,
        notebook_cells=state.notebook_cells,
        cell_refs_map=cell_refs_map,
        on_run_cell=_run_cell,
        on_stop_cell=_stop_cell,
        on_delete_cell=_delete_cell,
        on_move_cell=_move_cell,
        on_cell_change=_on_cell_change,
        on_clear_output=_clear_cell_output,
        is_expert_mode=is_expert_mode,
        on_pin_report=_pin_block_to_report,
        on_suggestion_selected=lambda p: (
            set_prompt_text(p),
            page.run_task(_submit_prompt, p),
        ),
    )

    add_cell_row = build_add_cell_row(
        on_add_cell=_add_cell,
        visible=bool(state.notebook_cells) or is_expert_mode,
    )

    empty_prompt = build_empty_state(
        on_import=lambda _: page.run_task(_pick_and_upload_file),
        on_autopilot=lambda _: page.run_task(
            run_autopilot_async,
            session_name,
            schema_json,
            credits,
            page,
            _add_cell,
            _run_cell,
        ),
        has_schema=bool(schema_json),
    )

    feed_controls = []
    if schema_json and not is_expert_mode:
        feed_controls.append(
            build_dataset_overview_card(
                dataset_name=state.active_project_dataset or "Active Dataset",
                schema=schema_json,
                page=page,
                initial_description=schema_json.get(
                    "description", "Dataset schema extracted and ready for analysis."
                ),
                suggestions=suggestions,
                on_suggestion_selected=lambda p: (
                    set_prompt_text(p),
                    page.run_task(_submit_prompt, p),
                ),
            )
        )

    if cell_controls:
        feed_controls.extend(cell_controls)
        feed_controls.append(add_cell_row)

    has_content = bool(state.notebook_cells) or bool(schema_json)

    scrollable_feed = ft.ListView(
        controls=feed_controls if (has_content and feed_controls) else [empty_prompt],
        expand=True,
        spacing=tokens.SPACE_SM,
        padding=ft.Padding(
            tokens.SPACE_MD, tokens.SPACE_SM, tokens.SPACE_MD, tokens.SPACE_MD
        ),
        auto_scroll=True,
    )

    # ── Bottom Bar Construction ──────────────────────────────────
    gen_indicator = build_gen_indicator(is_generating)

    chips_section = ft.Container(visible=False)
    if suggestions:
        chips_section = ft.Container(
            content=build_suggestion_chips(
                suggestions=suggestions,
                on_select=lambda p: (
                    set_prompt_text(p),
                    page.run_task(_submit_prompt, p),
                ),
                is_loading=suggestions_loading or is_generating,
                page=page,
                credit_service=credits,
            ),
            padding=ft.Padding(tokens.SPACE_MD, tokens.SPACE_XS, tokens.SPACE_MD, 0),
        )

    prompt_bar = build_prompt_bar(
        prompt_ref=prompt_ref,
        prompt_text=prompt_text,
        set_prompt_text=set_prompt_text,
        is_generating=is_generating,
        is_recording=is_recording,
        autopilot_running=state.autopilot_running,
        on_submit=lambda p: page.run_task(_submit_prompt, p),
        on_upload=lambda _: page.run_task(_pick_and_upload_file),
        on_toggle_voice=lambda _: page.run_task(_toggle_voice),
        on_toggle_expert_mode=lambda _: set_is_expert_mode(not is_expert_mode),
        is_expert_mode=is_expert_mode,
    )

    bottom_bar = ft.Column(
        controls=[
            gen_indicator,
            chips_section,
            prompt_bar,
        ],
        spacing=0,
    )

    return ft.Column(
        controls=[
            top_bar,
            scrollable_feed,
            bottom_bar,
        ],
        expand=True,
        spacing=0,
    )
