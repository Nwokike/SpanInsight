"""Survey-dataset bridge: export form responses as CSV datasets in Analysis.

Replaces the old inline-JSON cell dump. "Analyze in Notebook" now produces a
real CSV file that flows through the standard dataset import pipeline (upload
→ pd.read_csv → parquet snapshot), so surveys become first-class datasets.

Also owns return-refresh: when the user comes back to a project, tracked form
datasets are compared against the live response count and re-exported when new
submissions arrived (zero-stale-data guarantee the inline copy could never give).
"""

from __future__ import annotations

import asyncio
import logging
import re
import tempfile
from pathlib import Path

logger = logging.getLogger("FormsDatasetSync")


def build_form_file_name(title: str, form_id: str) -> str:
    """Deterministic, collision-free dataset name for a form's responses."""
    slug = re.sub(r"[^A-Za-z0-9_-]+", "_", (title or "survey")).strip("_")[:40]
    suffix = str(form_id)[-6:] if form_id else "000000"
    return f"{slug or 'survey'}_{suffix}_responses.csv"


def export_responses_to_csv(form_data: dict, responses: list[dict]) -> bytes:
    """Serialize responses to CSV bytes whose headers are question LABELS.

    Storage keys are mapped through the form's schema (raw key fallback for
    unknown/legacy ids, raw key on label collisions so columns stay unique).
    """
    from screens.forms.handlers import _form_schema_fields
    from services.forms_service import responses_to_csv_bytes

    labels = {
        str(f.get("name")): str(f.get("label") or f.get("name"))
        for f in _form_schema_fields(form_data)
        if f.get("name")
    }
    ordered_keys: list[str] = []
    for row in responses:
        data = row.get("data", row)
        for k in data:
            if k not in ordered_keys:
                ordered_keys.append(k)

    col_map: dict[str, str] = {}
    used: set[str] = set()
    for k in ordered_keys:
        label = labels.get(k, k)
        if label in used:
            label = k
        used.add(label)
        col_map[k] = label

    aliased = [
        {col_map[k]: v for k, v in row.get("data", row).items()} for row in responses
    ]
    return responses_to_csv_bytes(
        [{"data": r} for r in aliased], _form_schema_fields(form_data)
    )


async def write_csv_temp(file_name: str, csv_bytes: bytes) -> str:
    """Persist CSV bytes to a temp file; returns the local path."""

    def _write() -> str:
        local = str(Path(tempfile.gettempdir()) / file_name)
        Path(local).write_bytes(csv_bytes)
        return local

    return await asyncio.to_thread(_write)


async def record_form_dataset(
    projects,
    project_id: str,
    form_id: str,
    file_name: str,
    response_count: int,
) -> None:
    """Track a form-derived dataset on the project record (best effort).

    The project dict tolerates unknown keys, so ``form_datasets`` survives the
    regular save_notebook flow without schema changes anywhere else.
    """
    if not project_id or not projects:
        return
    try:
        proj = await projects.get_project(project_id)
        if not proj:
            return
        entries = [
            e for e in (proj.get("form_datasets") or []) if e.get("form_id") != form_id
        ]
        entries.append(
            {
                "form_id": form_id,
                "file_name": file_name,
                "last_count": int(response_count),
            }
        )
        proj["form_datasets"] = entries
        await projects.save_project(proj)
    except Exception as ex:
        logger.warning("Could not record form dataset provenance: %s", ex)


async def sync_form_datasets_on_mount(colab, projects, session_name: str, page):
    """Refresh tracked survey datasets when the user returns to a project.

    For every recorded form dataset: compare its stored response count against
    the live gateway count; when new submissions arrived, re-export the full
    CSV, overwrite the remote file, invalidate the stale parquet snapshot, and
    - if this survey is the project's ACTIVE dataset - reload ``df`` so the
    kernel sees the fresh rows too.
    """
    from core.state import state
    from services.file_service import snapshot_path_for, suggest_load_code
    from services.forms_service import fetch_all_responses, get_responses

    if not colab or not session_name or not state.active_project_id:
        return
    try:
        proj = await projects.get_project(state.active_project_id)
    except Exception as ex:
        logger.warning("Form-dataset sync: project load failed: %s", ex)
        return
    entries = (proj or {}).get("form_datasets") or []
    if not entries:
        return

    refreshed: list[str] = []
    for entry in entries:
        form_id = entry.get("form_id", "")
        file_name = entry.get("file_name", "")
        last_count = int(entry.get("last_count", 0))
        if not form_id or not file_name:
            continue
        try:
            current = await get_responses(form_id, state.active_project_id)
            live_count = int(current.get("count", 0))
            if live_count == last_count:
                continue

            rows = await fetch_all_responses(form_id, state.active_project_id)
            if not rows:
                continue

            # Need the schema to label columns: hydrate via public GET.
            from services.forms_service import get_form

            full = await get_form(form_id)
            form_like = {
                "title": (full or {}).get("title", file_name),
                "schema_json": (full or {}).get("schema_json", []),
            }
            csv_bytes = export_responses_to_csv(form_like, rows)
            local_path = await write_csv_temp(file_name, csv_bytes)

            remote_path = f"/content/{file_name}"
            await colab.upload(local_path, remote_path, session_name)
            # The cached parquet snapshot is now stale - drop it so the next
            # load re-parses the fresh CSV instead of serving old rows.
            snap = snapshot_path_for(file_name)
            await colab.exec_code(
                f"import os as _os\n_p = {snap!r}\n"
                "try:\n    _os.path.exists(_p) and _os.remove(_p)\nexcept Exception:\n    pass",
                session_name=session_name,
                timeout=15.0,
            )

            await record_form_dataset(
                projects, state.active_project_id, form_id, file_name, len(rows)
            )
            refreshed.append(f"{form_like['title']} (+{len(rows) - last_count})")

            # Active dataset? Refresh the kernel's df right away.
            if state.active_project_dataset == file_name:
                await colab.exec_code(
                    suggest_load_code(file_name),
                    session_name=session_name,
                    timeout=600.0,
                )
        except Exception as ex:
            logger.warning("Form-dataset sync failed for %s: %s", file_name, ex)

    if refreshed and page:
        try:
            from core.utils import show_snack

            show_snack(
                page,
                "🔄 Survey data refreshed: " + ", ".join(refreshed),
                success=True,
                duration=4000,
            )
        except Exception:
            pass
