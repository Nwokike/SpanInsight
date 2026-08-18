"""AnalysisScreen — Modular Colab notebook autopilot & AI Data Intelligence engine."""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path

import flet as ft
from flet import Control

from components.suggestion_chips import build_suggestion_chips
from core import tokens
from core.state import state
from core.utils import show_snack
from screens.analysis.export_ops import export_ipynb_async
from screens.analysis.fab_menu import build_analysis_fab
from screens.analysis.handlers import (
    connect_colab_async,
    pick_and_upload_file_async,
    run_autopilot_async,
    run_cell_async,
    submit_prompt_async,
)
from screens.analysis.layout import (
    build_analysis_feed,
    build_analysis_top_bar,
)
from screens.analysis.project_ops import (
    auto_reload_from_cache,
    create_new_project,
    load_notebook,
    save_notebook,
)
from screens.analysis.prompt_bar import build_gen_indicator, build_prompt_bar
from screens.analysis.session_banner import build_session_banner
from screens.analysis.voice_ops import toggle_voice_recording
from screens.files.modal import show_manage_files_modal
from state import AppStateCtx
from state.service_ctx import ServiceCtx

logger = logging.getLogger("AnalysisScreen")


@ft.component
def AnalysisScreen() -> Control:
    """Analysis engine — AI prompt, dataset intelligence, notebook cells, autopilot."""
    services = ft.use_context(ServiceCtx)
    app_state = ft.use_context(AppStateCtx)
    page = ft.context.page

    colab = services.colab
    credits = services.credits
    projects = services.projects

    # ── Local state ──────────────────────────────────────────────
    active_project_id, set_active_project_id = ft.use_state(state.active_project_id)
    active_project_name, set_active_project_name = ft.use_state(
        state.active_project_name or "Project 1"
    )
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

    def set_schema(schema: dict):
        state.active_schema_json = schema or {}
        set_schema_json(schema)

    # ── Refs ─────────────────────────────────────────────────────
    cell_refs_map = ft.use_ref({})
    prompt_ref = ft.Ref[ft.TextField]()
    session_name = app_state.active_session_name

    _save_debounce_ref = ft.use_ref(None)
    _pending_save_project_ref = ft.use_ref("")

    def _cancel_pending_save():
        pending = _save_debounce_ref.current
        if pending is not None and not pending.done():
            pending.cancel()
        _save_debounce_ref.current = None
        _pending_save_project_ref.current = ""

    def _cancel_pending_save_for_other_project(target_project: str):
        saved_for = _pending_save_project_ref.current
        if saved_for and saved_for != target_project:
            _cancel_pending_save()

    async def _debounced_save():
        try:
            await asyncio.sleep(2.0)
            await save_notebook(projects, schema_json, suggestions)
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.debug("Debounced notebook save skipped: %s", e)

    def _on_cell_change():
        set_cells_version(cells_version + 1)
        if page:
            _cancel_pending_save()
            _pending_save_project_ref.current = state.active_project_id
            _save_debounce_ref.current = page.run_task(_debounced_save)

    # ── Mount / Project Lifecycle ───────────────────────────────
    async def _on_mount():
        _cancel_pending_save_for_other_project(state.active_project_id)
        await load_notebook(
            projects=projects,
            session_name=session_name,
            page=page,
            colab=colab,
            set_schema=set_schema,
            set_suggestions=set_suggestions,
            set_cells_version=set_cells_version,
            cells_version=cells_version,
        )

    ft.use_effect(_on_mount, [active_project_id])

    def _on_project_selected(full_proj: dict):
        if not full_proj:
            return
        state.load_project(full_proj)
        set_active_project_id(full_proj.get("id", ""))
        set_active_project_name(full_proj.get("name", "Project 1"))
        schema = full_proj.get("schema_json", {})
        set_schema(schema)
        if schema.get("suggestions"):
            set_suggestions(schema["suggestions"])
        set_cells_version(cells_version + 1)

        from services.dataset_cache import get_cached_path

        cached = get_cached_path(full_proj.get("id", ""))
        if cached and session_name and page:
            page.run_task(
                auto_reload_from_cache,
                cached,
                session_name,
                colab,
                page,
                set_schema,
                set_cells_version,
                cells_version,
            )

    # ── Cell operations ──────────────────────────────────────────
    def _add_cell(cell_type: str = "code", source: str = ""):
        cell = state.add_cell(cell_type, source)
        _on_cell_change()
        return cell

    async def _run_cell(cell_id: str):
        live_sess = state.active_session_name or session_name
        await run_cell_async(
            cell_id,
            live_sess,
            colab,
            page,
            cell_refs_map,
            set_is_executing,
            _on_cell_change,
        )

    def _trigger_run_cell(cell_id: str):
        if page:
            page.run_task(_run_cell, cell_id)

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
        new_pinned = not block.get("pinned", False)
        block["pinned"] = new_pinned
        _on_cell_change()

        async def _sync_report():
            try:
                report_svc = getattr(services, "reports", None)
                if not report_svc:
                    from services.report_service import ReportService

                    report_svc = ReportService(services.storage)

                dataset_name = state.active_project_dataset or "Dataset Analysis"
                report_title = (
                    f"{Path(dataset_name).stem if dataset_name else 'Analysis'} Report"
                )

                png_b64 = block.get("figure_png_b64", "")
                if not png_b64 and block.get("figure_png"):
                    import base64

                    png_b64 = base64.b64encode(block["figure_png"]).decode("utf-8")
                if not png_b64:
                    for out in block.get("outputs", []):
                        if (
                            isinstance(out, dict)
                            and "data" in out
                            and "image/png" in out["data"]
                        ):
                            png_b64 = str(out["data"]["image/png"])
                            break

                stdout_text = ""
                for out in block.get("outputs", []):
                    if isinstance(out, dict):
                        if out.get("output_type") == "stream":
                            stdout_text += str(out.get("text", "")) + "\n"
                        elif "data" in out and "text/plain" in out["data"]:
                            stdout_text += str(out["data"]["text/plain"]) + "\n"

                report_block = {
                    "source_block_id": block.get("id"),
                    "prompt": block.get("prompt") or "Data Analysis",
                    "description": block.get("narration")
                    or block.get("description", ""),
                    "thought": block.get("thought", ""),
                    "figure_png_b64": png_b64,
                    "block_type": "chart" if png_b64 else "text",
                    "serialized_result": block.get("structured_result"),
                    "stdout": stdout_text.strip(),
                }

                existing_reports = await report_svc.list_reports()
                target_report = next(
                    (
                        r
                        for r in existing_reports
                        if r.get("dataset_name") == dataset_name
                        or r.get("title") == report_title
                    ),
                    None,
                )

                if new_pinned:
                    if target_report:
                        await report_svc.add_block_to_report(
                            target_report["id"], report_block
                        )
                    else:
                        await report_svc.create_report(
                            report_title, dataset_name, [report_block]
                        )
                else:
                    if target_report:
                        filtered = [
                            b
                            for b in target_report.get("blocks", [])
                            if b.get("source_block_id") != block.get("id")
                        ]
                        await report_svc.update_report(
                            target_report["id"], {"blocks": filtered}
                        )
            except Exception as ex:
                logger.warning("Report sync on pin failed: %s", ex)

        if page:
            page.run_task(_sync_report)
            show_snack(
                page,
                "📌 Pinned to Reports!" if new_pinned else "Unpinned from Reports",
                success=new_pinned,
            )

    # ── AI Overview & Suggestions ────────────────────────────────
    async def _fetch_ai_overview():
        if not schema_json:
            return
        from services.ai import analysis as ai_service

        for attempt in range(3):
            cur_desc = schema_json.get("description", "")
            if cur_desc and "unavailable" not in cur_desc.lower():
                break
            try:
                desc = await ai_service.describe_dataset(schema_json)
                if desc and "unavailable" not in desc.lower():
                    schema_json["description"] = desc
                    set_schema(dict(schema_json))
                    set_cells_version(cells_version + 1)
                    break
            except Exception as ex:
                logger.warning("AI describe failed (attempt %d): %s", attempt + 1, ex)
            if attempt < 2:
                await asyncio.sleep(2 * (attempt + 1))

        if (
            not suggestions
            and not schema_json.get("suggestions")
            and not state.notebook_cells
        ):
            set_suggestions_loading(True)
            try:
                from core.utils import build_analysis_context

                ctx = build_analysis_context(state.notebook_cells)
                desc = schema_json.get("description", "")
                try:
                    result = await ai_service.suggest(
                        schema_json, initial_description=desc, analysis_context=ctx
                    )
                except Exception as sug_ex:
                    logger.warning("Suggestions failed: %s", sug_ex)
                    result = ai_service.fallback_suggestions()
                if result:
                    set_suggestions(result)
            finally:
                set_suggestions_loading(False)

    ft.use_effect(_fetch_ai_overview, [bool(schema_json), active_project_id])

    # ── Cross-screen dataset handoff ────────────────────────────
    async def _process_pending_dataset_load():
        pending = state.pending_dataset_load
        if not pending or not session_name:
            return
        state.pending_dataset_load = None
        from screens.analysis.dataset_ops import run_dataset_import_dialog

        name = pending.get("name", "dataset")
        await run_dataset_import_dialog(
            page,
            colab,
            session_name,
            name,
            _add_cell,
            _run_cell,
            set_schema,
            set_is_generating=set_is_generating,
            remote_path=pending.get("remote_path") or f"/content/{name}",
        )

    ft.use_effect(
        _process_pending_dataset_load,
        [app_state.pending_dataset_load, session_name],
    )

    # ── Prompt & File actions ────────────────────────────────────
    async def _submit_prompt(p: str):
        if state.is_analyzing or state.autopilot_running:
            if page:
                show_snack(
                    page,
                    "⏳ Analysis already in progress — please wait",
                    duration=tokens.SNACK_DURATION_NORMAL_MS,
                )
            return
        try:
            state.is_analyzing = True
        except Exception:
            pass
        try:
            await submit_prompt_async(
                p,
                session_name,
                schema_json,
                credits,
                page,
                _add_cell,
                _run_cell,
                _fetch_ai_overview,
                set_is_generating,
                set_prompt_text,
                _on_cell_change,
                colab=colab,
            )
        finally:
            try:
                state.is_analyzing = False
            except Exception:
                pass

    async def _pick_and_upload_file():
        if state.is_analyzing or state.autopilot_running:
            if page:
                show_snack(
                    page,
                    "⏳ Analysis already in progress — please wait",
                    duration=tokens.SNACK_DURATION_NORMAL_MS,
                )
            return
        await pick_and_upload_file_async(
            session_name,
            colab,
            page,
            _add_cell,
            _run_cell,
            _fetch_ai_overview,
            set_schema,
            set_is_generating,
            on_autopilot_trigger=lambda s: page.run_task(
                run_autopilot_async,
                session_name,
                s,
                credits,
                page,
                _add_cell,
                _run_cell,
            ),
        )
        if projects and state.active_project_id and state.active_project_dataset:
            try:
                proj = await projects.get_project(state.active_project_id)
                if proj and (
                    proj["name"].startswith("Analysis ")
                    or proj["name"].startswith("Project ")
                ):
                    d_stem = Path(state.active_project_dataset).stem
                    all_p = await projects.list_projects()
                    similar = [
                        p
                        for p in all_p
                        if p.get("primary_dataset") == state.active_project_dataset
                    ]
                    new_name = (
                        d_stem if len(similar) <= 1 else f"{d_stem} ({len(similar)})"
                    )
                    proj["name"] = new_name
                    state.active_project_name = new_name
                    set_active_project_name(new_name)
                    await projects.save_project(proj)
                    set_cells_version(cells_version + 1)
            except Exception as ex:
                logger.debug("Project auto-rename: %s", ex)

    # ── FAB Sync ────────────────────────────────────────────────
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

    # ── Layout Assembly ──────────────────────────────────────────
    top_bar = build_analysis_top_bar(
        page=page,
        projects=projects,
        active_project_name=active_project_name,
        on_project_selected=_on_project_selected,
        on_new_project=lambda: page.run_task(
            create_new_project,
            projects,
            page,
            _cancel_pending_save,
            set_active_project_id,
            set_active_project_name,
            set_schema,
            set_suggestions,
            set_cells_version,
            cells_version,
        ),
        on_pick_file=lambda: page.run_task(_pick_and_upload_file),
        schema_json=schema_json,
        is_expert_mode=is_expert_mode,
        set_is_expert_mode=set_is_expert_mode,
        session_name=session_name,
    )

    feed = build_analysis_feed(
        page=page,
        schema_json=schema_json,
        is_expert_mode=is_expert_mode,
        suggestions=suggestions,
        cell_refs_map=cell_refs_map,
        on_trigger_run_cell=_trigger_run_cell,
        on_stop_cell=_stop_cell,
        on_delete_cell=_delete_cell,
        on_move_cell=_move_cell,
        on_cell_change=_on_cell_change,
        on_clear_output=_clear_cell_output,
        on_pin_block=_pin_block_to_report,
        on_submit_prompt=lambda p: (
            set_prompt_text(p),
            page.run_task(_submit_prompt, p),
        ),
        on_pick_file=lambda: page.run_task(_pick_and_upload_file),
        is_generating=is_generating,
        on_add_cell=_add_cell,
    )

    is_active_generating = (
        is_generating
        or getattr(app_state, "is_analyzing", False)
        or getattr(state, "is_analyzing", False)
    )
    gen_indicator = build_gen_indicator(
        is_active_generating,
        stage_text=state.autopilot_progress or "Reasoning & analyzing data…",
    )

    has_dataset = bool(schema_json) or bool(state.notebook_cells)
    chips_section = ft.Container(visible=False)
    if suggestions and has_dataset and is_expert_mode:
        chips_section = ft.Container(
            content=build_suggestion_chips(
                suggestions=suggestions,
                on_select=lambda p: (
                    set_prompt_text(p),
                    page.run_task(_submit_prompt, p),
                ),
                is_loading=suggestions_loading or is_active_generating,
                page=page,
                credit_service=credits,
            ),
            padding=ft.Padding(
                tokens.SPACE_MD,
                tokens.SPACE_XS,
                tokens.SPACE_MD,
                tokens.SPACE_NONE,
            ),
        )

    prompt_bar = build_prompt_bar(
        prompt_ref=prompt_ref,
        prompt_text=prompt_text,
        set_prompt_text=set_prompt_text,
        is_generating=is_active_generating,
        is_recording=is_recording,
        autopilot_running=state.autopilot_running,
        on_submit=lambda p: page.run_task(_submit_prompt, p),
        on_upload=lambda _: page.run_task(_pick_and_upload_file),
        on_toggle_voice=lambda _: page.run_task(
            toggle_voice_recording,
            page,
            is_recording,
            set_is_recording,
            set_prompt_text,
        ),
        on_toggle_expert_mode=lambda _: set_is_expert_mode(not is_expert_mode),
        is_expert_mode=is_expert_mode,
    )

    bottom_bar = ft.Column(
        controls=[
            gen_indicator,
            chips_section,
            prompt_bar,
        ],
        spacing=tokens.SPACE_NONE,
    )

    return ft.Column(
        controls=[
            top_bar,
            feed,
            bottom_bar,
        ],
        expand=True,
        spacing=tokens.SPACE_NONE,
    )
