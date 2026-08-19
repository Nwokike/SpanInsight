"""Shared dataset import pipeline: load → schema extraction → AI enrichment.

Used by three entry points so they behave identically:
- Analysis screen file import (``pick_and_upload_file_async``)
- Project auto-reload from the local dataset cache
- Files screen "Load in Analysis"

Every step reports failures to the caller instead of swallowing them - the
UI decides how to surface them (dialog with Retry, snackbar, etc.).
"""

from __future__ import annotations

import logging

import flet as ft

from core.state import state
from services.colab.introspection import (
    build_schema_extraction_code,
    parse_schema_from_outputs,
)

logger = logging.getLogger("DatasetOps")


async def extract_dataset_schema(
    colab, session_name: str
) -> tuple[dict | None, str | None]:
    """Run the silent schema extractor on Colab and parse its marker payload."""
    outputs = await colab.exec_code(
        build_schema_extraction_code(), session_name=session_name
    )
    return parse_schema_from_outputs(outputs)


async def load_and_extract_schema(
    colab,
    session_name: str,
    load_code: str,
    status_cb=None,
    add_cell_fn=None,
    run_cell_fn=None,
    cell_prompt: str | None = None,
) -> tuple[dict | None, str | None]:
    """Execute the dataset load code, then extract the schema.

    When ``add_cell_fn``/``run_cell_fn`` are provided the load runs as a
    visible notebook cell (transparency); otherwise it executes silently.
    """
    if add_cell_fn and run_cell_fn:
        cell = add_cell_fn("code", load_code)
        if cell_prompt:
            cell["prompt"] = cell_prompt
        # The schema pipeline narrates via enrich_schema_with_ai - skip the
        # generic per-cell post-exec AI for load cells.
        cell["skip_narration"] = True
        cell["is_initial_load"] = True
        await run_cell_fn(cell["id"])
        # The load cell's outputs hold the first honest failure signal
        last_error = next(
            (
                out
                for out in reversed(cell.get("outputs", []))
                if (out.get("output_type") or out.get("type")) == "error"
            ),
            None,
        )
        if last_error:
            trace = "\n".join(last_error.get("traceback", [])[-3:])
            return None, (
                f"Loading failed on Colab: "
                f"{last_error.get('ename', 'Error')}: {last_error.get('evalue', '')}"
                + (f"\n{trace}" if trace else "")
            )
    else:
        await colab.exec_code(load_code, session_name=session_name)

    if status_cb:
        status_cb("Analyzing schema & dataset statistics…")
    return await extract_dataset_schema(colab, session_name)


async def enrich_schema_with_ai(
    schema: dict,
    status_cb=None,
) -> dict:
    """Attach AI description + starter suggestions to a schema, with fallbacks.

    Mirrors v1 behaviour: the description is ALWAYS set (real text or honest
    fallback) and suggestions fall back to the built-in chips when the
    gateway is unreachable - the screen never renders empty.
    """
    from services.ai import analysis as ai_service

    if status_cb:
        status_cb("Compiling AI intelligence & suggestions…")

    if not schema.get("description"):
        # describe_dataset returns fallback text on failure
        schema["description"] = await ai_service.describe_dataset(schema)

    if not schema.get("suggestions"):
        try:
            suggs = await ai_service.suggest(
                schema, initial_description=schema.get("description", "")
            )
        except Exception as ex:
            logger.warning("AI suggestions failed, using fallbacks: %s", ex)
            suggs = ai_service.fallback_suggestions()
        schema["suggestions"] = suggs or ai_service.fallback_suggestions()

    state.suggestions = schema["suggestions"]
    return schema


def report_import_failure(page: ft.Page | None, file_name: str, reason: str | None):
    """Surface an import failure as a snackbar (used by non-dialog flows)."""
    if not page:
        return
    from core.utils import show_snack

    msg = reason or "Unknown error while analyzing the dataset."
    show_snack(page, f"⚠️ {file_name}: {msg}", error=True)


async def run_dataset_import_dialog(
    page: ft.Page | None,
    colab,
    session_name: str,
    file_name: str,
    add_cell_fn,
    run_cell_fn,
    set_schema_json,
    set_is_generating=None,
    upload_local_path: str | None = None,
    remote_path: str | None = None,
) -> bool:
    """Run the dataset import pipeline and extract schema with an active progress modal.

    - ``upload_local_path``: local file to upload first (Analysis import flow)
    - ``remote_path``: already-on-Colab path (Files "Load in Analysis" flow);
      defaults to ``/content/{file_name}``

    Returns True when the dataset is loaded, schema extracted and enriched.
    """
    import os

    from core import tokens
    from core.utils import show_snack
    from services.file_service import suggest_load_code

    remote = remote_path or f"/content/{file_name}"
    size_str = ""
    if upload_local_path and os.path.exists(upload_local_path):
        try:
            sz = os.path.getsize(upload_local_path)
            if sz < 1024:
                size_str = f" ({sz} B)"
            elif sz < 1024 * 1024:
                size_str = f" ({sz / 1024:.1f} KB)"
            else:
                size_str = f" ({sz / (1024 * 1024):.1f} MB)"
        except Exception:
            pass

    prog_bar = ft.ProgressBar(
        color=ft.Colors.PRIMARY,
        bgcolor=ft.Colors.with_opacity(tokens.OPACITY_CONTAINER, ft.Colors.PRIMARY),
    )
    status_text = ft.Text(
        f"Uploading to Colab VM…{size_str}"
        if upload_local_path
        else "Loading dataset…",
        size=tokens.FONT_XS,
        color=ft.Colors.ON_SURFACE_VARIANT,
    )
    upload_dialog = ft.AlertDialog(
        modal=True,
        title=ft.Row(
            [
                ft.Icon(
                    ft.Icons.TABLE_CHART_ROUNDED,
                    color=ft.Colors.PRIMARY,
                    size=tokens.ICON_MD,
                ),
                ft.Text(
                    f"Importing {file_name}",
                    size=tokens.FONT_MD,
                    weight=ft.FontWeight.W_600,
                ),
            ],
            spacing=tokens.SPACE_SM,
        ),
        content=ft.Column(
            [prog_bar, status_text],
            spacing=tokens.SPACE_SM,
            tight=True,
        ),
    )

    if page:
        page.show_dialog(upload_dialog)

    def _update_status(msg: str):
        status_text.value = msg
        try:
            status_text.update()
        except Exception:
            pass

    try:
        if upload_local_path:
            await colab.upload(upload_local_path, remote, session_name)

        _update_status("Loading dataset & building preview…")
        schema, error = await load_and_extract_schema(
            colab,
            session_name,
            suggest_load_code(file_name),
            status_cb=_update_status,
            add_cell_fn=add_cell_fn,
            run_cell_fn=run_cell_fn,
            cell_prompt=f"Load Dataset: {file_name}",
        )
        if schema is None:
            err_msg = error or "Could not read a tabular dataset."
            logger.error("Dataset load failed: %s", err_msg)
            if page:
                try:
                    page.pop_dialog()
                except Exception:
                    pass
                show_snack(page, f"Dataset load failed: {err_msg}", error=True)
            return False

        _update_status("Compiling AI intelligence & suggestions…")
        schema = await enrich_schema_with_ai(schema, status_cb=_update_status)

        state.suggestions = schema.get("suggestions", [])
        set_schema_json(schema)

        if page:
            try:
                page.pop_dialog()
            except Exception:
                pass
            show_snack(page, f"✅ Ready: {file_name}", success=True, duration=2500)
        return True
    except Exception as e:
        logger.error("Dataset import failed: %s", e)
        if page:
            try:
                page.pop_dialog()
            except Exception:
                pass
            show_snack(page, f"Import failed: {e}", error=True)
        return False
    finally:
        if page:
            try:
                page.pop_dialog()
            except Exception:
                pass
        if set_is_generating:
            set_is_generating(False)
