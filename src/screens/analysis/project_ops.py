"""Project lifecycle, persistence, and dataset cache reload operations for Analysis."""

from __future__ import annotations

import logging
from pathlib import Path

import flet as ft

from core.state import state
from core.utils import show_snack
from screens.analysis.dataset_ops import (
    enrich_schema_with_ai,
    load_and_extract_schema,
    report_import_failure,
)
from services.dataset_cache import get_cached_path
from services.file_service import suggest_load_code

logger = logging.getLogger("Analysis.ProjectOps")


async def auto_reload_from_cache(
    cached_path: Path,
    session_name: str,
    colab,
    page: ft.Page | None,
    set_schema,
    set_cells_version,
    cells_version: int,
):
    """Re-hydrate dataset onto Colab from local disk cache."""
    if not session_name or not colab:
        return
    try:
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


async def load_notebook(
    projects,
    session_name: str,
    page: ft.Page | None,
    colab,
    set_schema,
    set_suggestions,
    set_cells_version,
    cells_version: int,
):
    """Load notebook cells and dataset schema for active project."""
    try:
        if projects and state.active_project_id:
            proj = await projects.get_project(state.active_project_id)
            if proj:
                if not state.notebook_cells:
                    state.notebook_cells = list(proj.get("notebook_cells", []))
                dataset = proj.get("primary_dataset") or proj.get("dataset_name", "")
                if dataset:
                    state.active_project_dataset = dataset
                schema = state.active_schema_json or proj.get("schema_json", {})
                set_schema(schema)
                if schema.get("suggestions"):
                    set_suggestions(schema["suggestions"])
                elif proj.get("suggestions"):
                    set_suggestions(proj.get("suggestions", []))
                set_cells_version(cells_version + 1)

                cached = get_cached_path(state.active_project_id)
                if cached and not schema and session_name and page:
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
                return

        state.clear_notebook()
        set_schema({})
        set_suggestions([])
        set_cells_version(cells_version + 1)
    except Exception as e:
        logger.warning("Failed to load notebook: %s", e)


async def save_notebook(projects, schema_json: dict, suggestions: list):
    """Persist the current notebook, schema, and suggestions to disk."""
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


async def create_new_project(
    projects,
    page: ft.Page | None,
    cancel_pending_save_fn,
    set_active_project_id,
    set_active_project_name,
    set_schema,
    set_suggestions,
    set_cells_version,
    cells_version: int,
):
    """Create a fresh project and switch active state to it."""
    if not projects:
        return
    cancel_pending_save_fn()
    existing_list = await projects.list_projects()
    name = f"Project {len(existing_list) + 1}"
    new_p = await projects.create_project(name=name, hardware=state.session_hardware)
    state.load_project(new_p)
    set_active_project_id(new_p["id"])
    set_active_project_name(name)
    set_schema({})
    set_suggestions([])
    set_cells_version(cells_version + 1)
    if page:
        show_snack(page, f"✨ Created {name}", success=True)
