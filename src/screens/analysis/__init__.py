"""AnalysisScreen — Modular Colab notebook autopilot & AI Data Intelligence engine."""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path

import flet as ft
from flet import Control

from components.dataset_overview_card import build_dataset_overview_card
from components.file_import_card import build_file_import_card
from components.project_switcher import build_project_switcher
from components.suggestion_chips import build_suggestion_chips
from core import theme, tokens
from core.state import state
from screens.analysis.autopilot_bar import build_autopilot_bar
from screens.analysis.cell_list import build_add_cell_row, build_cells_container
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
        """Set screen schema AND mirror it to global state (used by run-cell AI hooks)."""
        state.active_schema_json = schema or {}
        set_schema_json(schema)

    # ── Refs ─────────────────────────────────────────────────────
    cell_refs_map = ft.use_ref({})
    prompt_ref = ft.Ref[ft.TextField]()

    session_name = app_state.active_session_name

    # ── Lifecycle: load/save notebook ───────────────────────────
    async def _on_mount():
        await _load_notebook()

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
        if cached and session_name:
            page.run_task(_auto_reload_from_cache, cached)

    async def _auto_reload_from_cache(cached_path):
        if not session_name:
            return
        try:
            from screens.analysis.dataset_ops import (
                enrich_schema_with_ai,
                load_and_extract_schema,
                report_import_failure,
            )
            from services.file_service import suggest_load_code

            file_name = cached_path.name
            remote_path = f"/content/{file_name}"
            await colab.upload(str(cached_path), remote_path, session_name)

            schema, error = await load_and_extract_schema(
                colab,
                session_name,
                suggest_load_code(file_name),
            )
            if schema is None:
                report_import_failure(page, file_name, error)
                return
            schema = await enrich_schema_with_ai(schema)
            set_schema(schema)
            set_cells_version(cells_version + 1)
        except Exception as ex:
            logger.warning("Auto-reload dataset from cache failed: %s", ex)
            report_import_failure(page, cached_path.name, str(ex))

    async def _load_notebook():
        # Cancel a pending save ONLY if we're loading a different project —
        # same-project remounts (tab away & back) must let it flush, otherwise
        # fresh outputs/charts/descriptions vanish after navigation.
        _cancel_pending_save_for_other_project(state.active_project_id)
        try:
            if projects and state.active_project_id:
                proj = await projects.get_project(state.active_project_id)
                if proj:
                    if not state.notebook_cells:
                        state.notebook_cells = list(proj.get("notebook_cells", []))
                    dataset = proj.get("primary_dataset") or proj.get(
                        "dataset_name", ""
                    )
                    if dataset:
                        state.active_project_dataset = dataset
                    schema = state.active_schema_json or proj.get("schema_json", {})
                    set_schema(schema)
                    if schema.get("suggestions"):
                        set_suggestions(schema["suggestions"])
                    elif proj.get("suggestions"):
                        set_suggestions(proj.get("suggestions", []))
                    set_cells_version(cells_version + 1)

                    from services.dataset_cache import get_cached_path

                    cached = get_cached_path(state.active_project_id)
                    if cached and not schema and session_name:
                        page.run_task(_auto_reload_from_cache, cached)
                    return
            # If no active project or project was deleted, keep state cleanly isolated
            state.clear_notebook()
            set_schema({})
            set_suggestions([])
            set_cells_version(cells_version + 1)
        except Exception as e:
            logger.warning("Failed to load notebook: %s", e)

    async def _save_notebook():
        try:
            if projects and state.active_project_id:
                proj = await projects.get_project(state.active_project_id)
                if proj:
                    proj["notebook_cells"] = state.notebook_cells
                    proj["session_name"] = state.active_session_name
                    if state.active_project_dataset:
                        proj["primary_dataset"] = state.active_project_dataset
                        proj["dataset_name"] = state.active_project_dataset
                    current_schema = schema_json or state.active_schema_json
                    if current_schema:
                        proj["schema_json"] = current_schema
                    if suggestions:
                        proj["suggestions"] = suggestions
                    await projects.save_project(proj)
        except Exception as e:
            logger.warning("Failed to save notebook: %s", e)

    _save_debounce_ref = ft.use_ref(None)
    _pending_save_project_ref = ft.use_ref("")

    async def _debounced_save():
        """v1's proven debounce pattern: bursts of cell changes collapse into
        one write ~2s after the last change. Full-project JSON dumps on every
        single change used to saturate the event loop and freeze the UI."""
        try:
            await asyncio.sleep(2.0)
            await _save_notebook()
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.debug("Debounced notebook save skipped: %s", e)

    def _cancel_pending_save():
        pending = _save_debounce_ref.current
        if pending is not None and not pending.done():
            pending.cancel()
        _save_debounce_ref.current = None
        _pending_save_project_ref.current = ""

    def _cancel_pending_save_for_other_project(target_project: str):
        """Cancel a pending save ONLY when switching projects.

        Remounting the same project (tab away & back) must keep the pending
        save alive — cancelling it was wiping freshly rendered outputs,
        charts and descriptions after navigation.
        """
        saved_for = _pending_save_project_ref.current
        if saved_for and saved_for != target_project:
            _cancel_pending_save()

    def _on_cell_change():
        set_cells_version(cells_version + 1)
        if page:
            _cancel_pending_save()
            _pending_save_project_ref.current = state.active_project_id
            _save_debounce_ref.current = page.run_task(_debounced_save)

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
            from core.utils import show_snack

            show_snack(
                page,
                "📌 Pinned to Reports!" if new_pinned else "Unpinned from Reports",
                success=new_pinned,
            )

    # ── AI Overview & Suggestions ────────────────────────────────
    async def _fetch_ai_overview():
        if not schema_json:
            return
        import asyncio

        from services.ai import analysis as ai_service

        # 1. Fetch AI description if missing or previously failed (retry with backoff)
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
                logger.warning(
                    "AI describe_dataset failed (attempt %d): %s", attempt + 1, ex
                )
            if attempt < 2:
                await asyncio.sleep(2 * (attempt + 1))

        # 2. Fetch AI starter suggestions ONLY if no suggestions and no cells exist yet
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
                    logger.warning("Suggestions failed, using fallbacks: %s", sug_ex)
                    result = ai_service.fallback_suggestions()
                if result:
                    set_suggestions(result)
            finally:
                set_suggestions_loading(False)

    ft.use_effect(_fetch_ai_overview, [bool(schema_json), active_project_id])

    # ── Cross-screen dataset handoff (Files → Analysis) ─────────
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

    # ── Quick action file picker trigger from Home ──────────────
    async def _check_trigger_file_picker():
        if getattr(state, "trigger_file_picker", False):
            state.trigger_file_picker = False
            await _pick_and_upload_file()

    ft.use_effect(
        _check_trigger_file_picker,
        [app_state.trigger_file_picker, session_name],
    )

    # ── Prompt & File actions ────────────────────────────────────
    def _busy_snack():
        if page:
            from core.utils import show_snack

            show_snack(
                page,
                "⏳ Analysis already in progress — please wait for it to finish",
                duration=2500,
            )

    async def _submit_prompt(p: str):
        # Hard guard against double-submission (double credit spend): the UI
        # disables inputs, but this check survives stale render closures.
        if state.is_analyzing or state.autopilot_running:
            _busy_snack()
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
            # Observable set notifies subscribers → may touch a destroyed
            # session if the app closed mid-generation; never crash on that.
            try:
                state.is_analyzing = False
            except Exception:
                pass

    async def _pick_and_upload_file():
        if state.is_analyzing or state.autopilot_running:
            _busy_snack()
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
        # Rename project if default
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
                    if len(similar) <= 1:
                        new_name = d_stem
                    else:
                        new_name = f"{d_stem} ({len(similar)})"
                    proj["name"] = new_name
                    state.active_project_name = new_name
                    set_active_project_name(new_name)
                    await projects.save_project(proj)
                    set_cells_version(cells_version + 1)
            except Exception as ex:
                logger.debug("Project auto-rename: %s", ex)

    async def _create_new_project(_=None):
        if not projects:
            return
        _cancel_pending_save()  # never save old-project cells into the new one
        existing_list = await projects.list_projects()
        name = f"Project {len(existing_list) + 1}"
        new_p = await projects.create_project(
            name=name, hardware=state.session_hardware
        )
        state.load_project(new_p)
        set_active_project_id(new_p["id"])
        set_active_project_name(name)
        set_schema({})
        set_suggestions([])
        set_cells_version(cells_version + 1)
        if page:
            from core.utils import show_snack

            show_snack(page, f"✨ Created {name}", success=True)

    async def _toggle_voice():
        if is_recording:
            set_is_recording(False)
            try:
                from services.audio_service import AudioService as _AS

                _audio_svc = _AS(page)
                result = await _audio_svc.stop_recording()
                if result:
                    audio_bytes, mime_type = result
                    from services.ai import transcribe_audio

                    text = await transcribe_audio(audio_bytes, mime_type)
                    if text and not text.startswith("["):
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
                        from core.utils import show_snack

                        show_snack(
                            page,
                            "Microphone unavailable on this platform. Please type your query.",
                            error=True,
                        )
            except Exception as ex:
                set_is_recording(False)
                if page:
                    from core.utils import show_snack

                    show_snack(page, f"Voice recording not supported: {ex}", error=True)

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

    # Segmented Mode Switcher (KTV-Player style)
    insight_bg = theme.PRIMARY if not is_expert_mode else ft.Colors.TRANSPARENT
    insight_fg = ft.Colors.WHITE if not is_expert_mode else ft.Colors.ON_SURFACE_VARIANT
    expert_bg = theme.PRIMARY if is_expert_mode else ft.Colors.TRANSPARENT
    expert_fg = ft.Colors.WHITE if is_expert_mode else ft.Colors.ON_SURFACE_VARIANT

    mode_switch_bar = ft.Container(
        padding=ft.Padding(2, 2, 2, 2),
        height=30,
        border_radius=tokens.RADIUS_SM,
        bgcolor=ft.Colors.with_opacity(0.08, ft.Colors.ON_SURFACE),
        border=ft.Border.all(1, ft.Colors.with_opacity(0.12, ft.Colors.ON_SURFACE)),
        content=ft.Row(
            controls=[
                ft.Container(
                    content=ft.Row(
                        [
                            ft.Icon(
                                ft.Icons.AUTO_AWESOME_ROUNDED,
                                size=12,
                                color=insight_fg,
                            ),
                            ft.Text(
                                "Insight",
                                size=tokens.FONT_XS,
                                weight=ft.FontWeight.BOLD
                                if not is_expert_mode
                                else ft.FontWeight.NORMAL,
                                color=insight_fg,
                            ),
                        ],
                        spacing=3,
                        alignment=ft.MainAxisAlignment.CENTER,
                        tight=True,
                    ),
                    bgcolor=insight_bg,
                    border_radius=tokens.RADIUS_SM,
                    padding=ft.Padding(8, 3, 8, 3),
                    ink=True,
                    on_click=lambda _: set_is_expert_mode(False),
                ),
                ft.Container(
                    content=ft.Row(
                        [
                            ft.Icon(ft.Icons.CODE_ROUNDED, size=12, color=expert_fg),
                            ft.Text(
                                "Expert",
                                size=tokens.FONT_XS,
                                weight=ft.FontWeight.BOLD
                                if is_expert_mode
                                else ft.FontWeight.NORMAL,
                                color=expert_fg,
                            ),
                        ],
                        spacing=3,
                        alignment=ft.MainAxisAlignment.CENTER,
                        tight=True,
                    ),
                    bgcolor=expert_bg,
                    border_radius=tokens.RADIUS_SM,
                    padding=ft.Padding(8, 3, 8, 3),
                    ink=True,
                    on_click=lambda _: set_is_expert_mode(True),
                ),
            ],
            spacing=2,
            tight=True,
        ),
    )

    project_chip = build_project_switcher(
        page,
        projects,
        active_project_name=active_project_name,
        on_project_selected=_on_project_selected,
    )

    new_project_btn = ft.FilledButton(
        "New Project",
        icon=ft.Icons.ADD_ROUNDED,
        style=ft.ButtonStyle(
            bgcolor=ft.Colors.with_opacity(0.12, theme.PRIMARY),
            color=theme.PRIMARY,
            shape=ft.RoundedRectangleBorder(radius=tokens.RADIUS_SM),
            padding=ft.Padding(10, 4, 10, 4),
        ),
        height=30,
        on_click=lambda _: page.run_task(_create_new_project),
    )

    dataset_label = state.active_project_dataset or (
        schema_json.get("name") if schema_json else ""
    )
    dataset_indicator = ft.Container()
    if dataset_label:
        dataset_indicator = ft.Container(
            content=ft.Row(
                [
                    ft.Icon(
                        ft.Icons.DATASET_ROUNDED,
                        size=14,
                        color=theme.ACCENT,
                    ),
                    ft.Text(
                        dataset_label,
                        size=tokens.FONT_XS,
                        weight=ft.FontWeight.W_600,
                        color=theme.ACCENT,
                        max_lines=1,
                        overflow=ft.TextOverflow.ELLIPSIS,
                    ),
                    ft.IconButton(
                        icon=ft.Icons.REFRESH_ROUNDED,
                        icon_size=13,
                        tooltip="Change Dataset",
                        on_click=lambda _: page.run_task(_pick_and_upload_file),
                        style=ft.ButtonStyle(padding=2),
                    ),
                ],
                spacing=tokens.SPACE_XXS,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                tight=True,
            ),
            padding=ft.Padding(8, 4, 8, 4),
            height=30,
            border_radius=tokens.RADIUS_SM,
            bgcolor=ft.Colors.with_opacity(0.08, theme.ACCENT),
        )

    top_bar = ft.Column(
        controls=[
            ft.Container(
                content=ft.Row(
                    controls=[
                        project_chip,
                        dataset_indicator,
                        new_project_btn,
                        mode_switch_bar,
                        session_chip,
                    ],
                    alignment=ft.MainAxisAlignment.START,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=tokens.SPACE_SM,
                    scroll=ft.ScrollMode.ADAPTIVE,
                ),
                padding=ft.Padding(
                    tokens.SPACE_MD, tokens.SPACE_SM, tokens.SPACE_MD, tokens.SPACE_XXS
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
        on_run_cell=_trigger_run_cell,
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

    # + Code and + Markdown ONLY visible in Expert Mode
    add_cell_row = build_add_cell_row(
        on_add_cell=_add_cell,
        visible=is_expert_mode,
    )

    has_dataset = bool(schema_json) or bool(state.notebook_cells)

    import_area = build_file_import_card(
        on_pick=lambda: page.run_task(_pick_and_upload_file),
        is_loading=is_generating,
    )

    active_desc = schema_json.get("description", "")

    def _open_raw_data_dialog():
        if not schema_json or not page:
            return
        head_records = schema_json.get("head", [])
        if not head_records:
            from core.utils import show_snack

            show_snack(page, "No preview rows available for this dataset.")
            return

        cols = list(head_records[0].keys()) if head_records else []
        dt_cols = [
            ft.DataColumn(
                ft.Text(str(c)[:16], size=tokens.FONT_XS, weight=ft.FontWeight.W_600)
            )
            for c in cols
        ]
        dt_rows = []
        for r in head_records:
            cells = [
                ft.DataCell(
                    ft.Text(
                        str(r.get(c, "—")),
                        size=tokens.FONT_XS,
                        font_family="RobotoMono",
                    )
                )
                for c in cols
            ]
            dt_rows.append(ft.DataRow(cells=cells))

        dlg = ft.AlertDialog(
            title=ft.Text(
                f"Dataset Preview ({state.active_project_dataset or 'Active Dataset'})",
                size=tokens.FONT_MD,
                weight=ft.FontWeight.W_600,
            ),
            content=ft.Container(
                content=ft.Row(
                    controls=[
                        ft.DataTable(
                            columns=dt_cols,
                            rows=dt_rows,
                            heading_row_height=36,
                            data_row_max_height=32,
                            column_spacing=18,
                        )
                    ],
                    scroll=ft.ScrollMode.AUTO,
                ),
                width=650,
                height=260,
            ),
            actions=[
                ft.TextButton("Close", on_click=lambda _: page.pop_dialog()),
            ],
        )
        page.show_dialog(dlg)

    feed_controls = []
    if schema_json and not is_expert_mode:
        feed_controls.append(
            build_dataset_overview_card(
                dataset_name=state.active_project_dataset or "Active Dataset",
                schema=schema_json,
                page=page,
                initial_description=active_desc,
                suggestions=suggestions,
                on_suggestion_selected=lambda p: (
                    set_prompt_text(p),
                    page.run_task(_submit_prompt, p),
                ),
                on_view_raw_data=_open_raw_data_dialog,
                on_inspect_schema=lambda: __import__(
                    "components.dataset_inspector",
                    fromlist=["show_dataset_inspector"],
                ).show_dataset_inspector(
                    page,
                    state.active_project_dataset or "Active Dataset",
                    schema_json,
                ),
            )
        )

    if cell_controls:
        feed_controls.extend(cell_controls)

    # In Expert Mode: show + Code / + Markdown
    if is_expert_mode:
        feed_controls.append(add_cell_row)

    scrollable_feed = ft.ListView(
        controls=feed_controls if (has_dataset and feed_controls) else [import_area],
        expand=True,
        spacing=tokens.SPACE_SM,
        padding=ft.Padding(
            tokens.SPACE_MD, tokens.SPACE_SM, tokens.SPACE_MD, tokens.SPACE_MD
        ),
        auto_scroll=True,
    )

    # ── Bottom Bar Construction ──────────────────────────────────
    is_active_generating = (
        is_generating
        or getattr(app_state, "is_analyzing", False)
        or getattr(state, "is_analyzing", False)
    )
    gen_indicator = build_gen_indicator(
        is_active_generating,
        stage_text=state.autopilot_progress or "Reasoning & analyzing data…",
    )

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
            padding=ft.Padding(tokens.SPACE_MD, tokens.SPACE_XS, tokens.SPACE_MD, 0),
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
