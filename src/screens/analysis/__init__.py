"""AnalysisScreen — Modular Colab notebook autopilot & AI Data Intelligence engine."""

from __future__ import annotations

import json
import logging
from pathlib import Path

import flet as ft
from flet import Control

from components.dataset_overview_card import build_dataset_overview_card
from components.file_import_card import build_file_import_card
from components.project_switcher import build_project_switcher
from components.suggestion_chips import build_suggestion_chips
from core import theme, tokens
from core.constants import STORAGE_NOTEBOOKS
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
    storage = services.storage
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
        set_schema_json(schema)
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
            from services.file_service import suggest_load_code

            file_name = cached_path.name
            remote_path = f"/content/{file_name}"
            await colab.upload(str(cached_path), remote_path, session_name)
            load_code = suggest_load_code(file_name)
            await colab.exec_code(load_code, session_name=session_name)

            schema_code = (
                "import json\n"
                "try:\n"
                "  _schema = {\n"
                '    "shape": list(df.shape),\n'
                '    "columns": list(df.columns),\n'
                '    "dtypes": {str(k): str(v) for k, v in df.dtypes.items()},\n'
                '    "summary": df.describe(include="all").to_dict(),\n'
                '    "head": df.head(5).to_dict(orient="records"),\n'
                '    "nulls": df.isnull().sum().to_dict(),\n'
                "  }\n"
                "  print('__SPANINSIGHT_SCHEMA_START__')\n"
                "  print(json.dumps(_schema, default=str))\n"
                "  print('__SPANINSIGHT_SCHEMA_END__')\n"
                "except Exception:\n"
                "  pass\n"
            )
            res = await colab.exec_code(schema_code, session_name=session_name)
            raw_text = ""
            if res and isinstance(res, dict):
                for out in res.get("outputs", []):
                    if out.get("output_type") == "stream":
                        raw_text += out.get("text", "")
                    elif out.get("data", {}).get("text/plain"):
                        raw_text += str(out["data"]["text/plain"])

            if "__SPANINSIGHT_SCHEMA_START__" in raw_text:
                json_part = (
                    raw_text.split("__SPANINSIGHT_SCHEMA_START__")[1]
                    .split("__SPANINSIGHT_SCHEMA_END__")[0]
                    .strip()
                )
                parsed = json.loads(json_part)
                set_schema_json(parsed)
                set_cells_version(cells_version + 1)
        except Exception as ex:
            logger.warning("Auto-reload dataset from cache failed: %s", ex)

    async def _load_notebook():
        try:
            if projects and state.active_project_id:
                proj = await projects.get_project(state.active_project_id)
                if proj:
                    state.notebook_cells = list(proj.get("notebook_cells", []))
                    if proj.get("dataset_name"):
                        state.active_project_dataset = proj["dataset_name"]
                    if proj.get("schema_json"):
                        set_schema_json(proj["schema_json"])
                    set_cells_version(cells_version + 1)

                    from services.dataset_cache import get_cached_path

                    cached = get_cached_path(state.active_project_id)
                    if cached and not proj.get("schema_json") and session_name:
                        page.run_task(_auto_reload_from_cache, cached)
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
                    if state.active_project_dataset:
                        proj["dataset_name"] = state.active_project_dataset
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

    # ── AI Overview & Suggestions ────────────────────────────────
    async def _fetch_ai_overview():
        if not schema_json:
            return
        # 1. Fetch AI description if missing
        if not schema_json.get("description"):
            try:
                from services.ai import analysis as ai_service

                desc = await ai_service.describe_dataset(schema_json)
                if desc:
                    schema_json["description"] = desc
                    set_schema_json(dict(schema_json))
                    set_cells_version(cells_version + 1)
            except Exception as ex:
                logger.warning("AI describe_dataset failed: %s", ex)

        # 2. Fetch AI starter suggestions if missing
        if not suggestions:
            set_suggestions_loading(True)
            try:
                from services.ai import analysis as ai_service

                ctx = "\n".join(
                    c.get("source", "")[:80]
                    for c in state.notebook_cells
                    if c.get("type") == "code" and c.get("source")
                )
                desc = schema_json.get("description", "")
                result = await ai_service.suggest(
                    schema_json, initial_description=desc, analysis_context=ctx
                )
                if result:
                    set_suggestions(result)
            except Exception as e:
                logger.warning("Suggestions failed: %s", e)
            finally:
                set_suggestions_loading(False)

    ft.use_effect(_fetch_ai_overview, [bool(schema_json), active_project_id])

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
            _fetch_ai_overview,
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
            _fetch_ai_overview,
            set_schema_json,
            set_is_generating,
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
        existing_list = await projects.list_projects()
        name = f"Project {len(existing_list) + 1}"
        new_p = await projects.create_project(
            name=name, hardware=state.session_hardware
        )
        state.load_project(new_p)
        set_active_project_id(new_p["id"])
        set_active_project_name(name)
        set_schema_json({})
        set_suggestions([])
        set_cells_version(cells_version + 1)
        if page:
            page.snack_bar = ft.SnackBar(ft.Text(f"✨ Created {name}"))
            page.snack_bar.open = True
            page.update()

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

    active_suggestions = (
        suggestions if suggestions else schema_json.get("suggestions", [])
    )
    active_desc = schema_json.get(
        "description", "Dataset schema extracted and ready for analysis."
    )

    feed_controls = []
    if schema_json and not is_expert_mode:
        feed_controls.append(
            build_dataset_overview_card(
                dataset_name=state.active_project_dataset or "Active Dataset",
                schema=schema_json,
                page=page,
                initial_description=active_desc,
                suggestions=active_suggestions,
                on_suggestion_selected=lambda p: (
                    set_prompt_text(p),
                    page.run_task(_submit_prompt, p),
                ),
            )
        )

    if cell_controls:
        feed_controls.extend(cell_controls)

    # In Expert Mode: show + Code / + Markdown
    if is_expert_mode:
        feed_controls.append(add_cell_row)

    # In Insight View: show Suggestions at the bottom of the feed
    if active_suggestions and not is_expert_mode and has_dataset:
        sugg_chips_feed = []
        for s in active_suggestions[:4]:
            if isinstance(s, dict):
                label_txt = s.get("label") or s.get("prompt", "")
                icon_txt = s.get("icon", "✨")
                prompt_val = s.get("prompt") or label_txt
                disp = f"{icon_txt} {label_txt}".strip()
            else:
                prompt_val = str(s)
                disp = str(s)

            sugg_chips_feed.append(
                ft.ActionChip(
                    label=ft.Text(disp, size=tokens.FONT_XS),
                    tooltip=prompt_val,
                    on_click=lambda _, p=prompt_val: (
                        set_prompt_text(p),
                        page.run_task(_submit_prompt, p),
                    ),
                )
            )

        feed_controls.append(
            ft.Container(
                content=ft.Column(
                    [
                        ft.Row(
                            [
                                ft.Icon(
                                    ft.Icons.LIGHTBULB_ROUNDED,
                                    size=16,
                                    color=theme.ACCENT,
                                ),
                                ft.Text(
                                    "Next Recommended Analyses:",
                                    size=tokens.FONT_SM,
                                    weight=ft.FontWeight.W_700,
                                ),
                            ],
                            spacing=tokens.SPACE_XXS,
                        ),
                        ft.Row(sugg_chips_feed, wrap=True, spacing=tokens.SPACE_XS),
                    ],
                    spacing=tokens.SPACE_XS,
                ),
                padding=tokens.SPACE_MD,
                border_radius=tokens.RADIUS_MD,
                bgcolor=ft.Colors.with_opacity(0.04, theme.ACCENT),
                border=ft.Border.all(1, ft.Colors.with_opacity(0.12, theme.ACCENT)),
                margin=ft.Margin(0, tokens.SPACE_XS, 0, tokens.SPACE_SM),
            )
        )

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
    gen_indicator = build_gen_indicator(is_generating)

    chips_section = ft.Container(visible=False)
    if suggestions and has_dataset:
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
