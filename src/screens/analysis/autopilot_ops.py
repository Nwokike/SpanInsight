"""AI prompt generation, dataset file loading, and autopilot engine handlers."""

from __future__ import annotations

import asyncio
import logging

import flet as ft

from core.constants import COST_AUTOPILOT, COST_CUSTOM_PROMPT
from core.state import state
from core.utils import show_snack

logger = logging.getLogger("AutopilotHandlers")


async def submit_prompt_async(
    prompt: str,
    session_name: str,
    schema_json: dict,
    credits,
    page: ft.Page,
    add_cell_fn,
    run_cell_fn,
    fetch_suggestions_fn,
    set_is_generating,
    set_prompt_text,
    on_cell_change,
):
    """Handle natural-language AI query, generate Python, and execute."""
    if not prompt.strip():
        return
    if not session_name:
        if page:
            show_snack(page, "Connect to Colab first", error=True)
        return

    set_is_generating(True)
    set_prompt_text("")

    try:
        if credits:
            ok, _ = await credits.spend(COST_CUSTOM_PROMPT)
            if not ok:
                if page:
                    show_snack(page, "Not enough credits", error=True)
                return

        from services.ai import analysis as ai_service

        meta = await ai_service.generate_code_meta(prompt, schema_json)
        code = meta.get("code", "")
        if not code:
            if page:
                show_snack(
                    page,
                    "AI couldn't generate code. Try rephrasing.",
                    error=True,
                )
            return

        cell = add_cell_fn("code", code)
        cell["prompt"] = prompt
        cell["thought"] = meta.get("thought", "")
        cell["thought_duration"] = meta.get("duration", 0.0)
        cell["model"] = meta.get("model", "")
        set_is_generating(False)
        await run_cell_fn(cell["id"])

    except asyncio.CancelledError:
        logger.info("Prompt submission cancelled (app closing)")
        return
    except Exception as e:
        logger.error("Prompt submission failed: %s", e)
        if page:
            try:
                show_snack(page, f"Error: {e}", error=True)
            except Exception:
                pass
    finally:
        try:
            set_is_generating(False)
        except Exception:
            pass


async def pick_and_upload_file_async(
    session_name: str,
    colab,
    page: ft.Page,
    add_cell_fn,
    run_cell_fn,
    fetch_suggestions_fn,
    set_schema_json,
    set_is_generating,
    on_autopilot_trigger=None,
):
    """FilePicker dialog, upload to Colab /content/, generate load code, and extract schema."""
    active_sess = state.active_session_name or session_name
    if not active_sess and colab:
        try:
            sessions = await colab.list_sessions()
            if sessions and isinstance(sessions, list):
                active_sess = sessions[0]["name"]
                state.active_session_name = active_sess
        except Exception:
            pass

    picker = getattr(page, "file_picker", None)
    if not picker:
        if page:
            show_snack(page, "File picker service not available", error=True)
        return

    result = await picker.pick_files(
        allow_multiple=False,
        dialog_title="Select Dataset or Scientific Data File",
    )

    if result and result[0].path:
        picked = result[0]
        set_is_generating(True)

        from services.dataset_cache import cache_file

        if state.active_project_id:
            cache_file(state.active_project_id, picked.path)
        state.active_project_dataset = picked.name

        try:
            from services.file_service import validate_file

            validate_file(picked.path)
        except Exception as e:
            logger.error("File validation failed: %s", e)
            set_is_generating(False)
            if page:
                show_snack(page, f"Import failed: {e}", error=True)
            return

        active_sess = state.active_session_name or session_name
        if not active_sess:
            if page:
                show_snack(page, "Connect to Colab first", error=True)
            set_is_generating(False)
            return

        from screens.analysis.dataset_ops import run_dataset_import_dialog

        ok = await run_dataset_import_dialog(
            page,
            colab,
            active_sess,
            picked.name,
            add_cell_fn,
            run_cell_fn,
            set_schema_json,
            set_is_generating=set_is_generating,
            upload_local_path=picked.path,
        )

        if ok and getattr(state, "autopilot_enabled", False):
            state.autopilot_enabled = False
            schema = state.active_schema_json or {}
            if on_autopilot_trigger and schema:
                on_autopilot_trigger(schema)


async def run_autopilot_async(
    session_name: str,
    schema_json: dict,
    credits,
    page: ft.Page,
    add_cell_fn,
    run_cell_fn,
):
    """Execute autonomous multi-step analytical autopilot."""
    active_sess = state.active_session_name or session_name
    if not active_sess or not schema_json:
        if page:
            show_snack(page, "Upload a dataset first to use Autopilot", error=True)
        return

    if credits:
        ok, _ = await credits.spend(COST_AUTOPILOT)
        if not ok:
            if page:
                show_snack(page, "Not enough credits for Autopilot", error=True)
            return

    state.autopilot_running = True
    state.autopilot_cancelled = False
    state.autopilot_progress = "Starting autopilot..."
    max_steps = 8

    from services.ai import analysis as ai_service

    history = []
    try:
        initial_desc = await ai_service.describe_dataset(schema_json)
    except Exception as ex:
        logger.warning("Autopilot initial describe failed: %s", ex)
        initial_desc = "Dataset loaded"

    for step in range(max_steps):
        if state.autopilot_cancelled:
            state.autopilot_progress = "Autopilot cancelled"
            break

        state.autopilot_progress = f"Step {step + 1}/{max_steps}..."

        try:
            plan = await ai_service.plan_next_step(schema_json, initial_desc, history)
            if plan.get("is_complete"):
                state.autopilot_progress = (
                    f"Done — {plan.get('reason', 'Analysis complete')}"
                )
                break

            prompt = plan.get("prompt", "")
            if not prompt:
                break

            meta = await ai_service.generate_code_meta(
                prompt,
                schema_json,
                analysis_context="\n".join(h.get("prompt", "") for h in history),
            )
            code = meta.get("code", "")
            if not code:
                continue

            cell = add_cell_fn("code", code)
            cell["prompt"] = prompt
            cell["thought"] = meta.get("thought", "")
            cell["thought_duration"] = meta.get("duration", 0.0)
            cell["model"] = meta.get("model", "")
            # Autopilot narrates each step itself — skip per-cell post-exec AI
            cell["skip_narration"] = True
            await run_cell_fn(cell["id"])

            success = True
            desc = ""
            if cell.get("outputs"):
                last_out = cell["outputs"][-1]
                if last_out.get("output_type") == "error":
                    success = False
                    desc = "\n".join(last_out.get("traceback", []))[:200]
                else:
                    try:
                        desc = await ai_service.describe_result(
                            initial_desc,
                            {"prompt": prompt, "code": code},
                        )
                    except Exception as desc_ex:
                        logger.warning("Autopilot step narration failed: %s", desc_ex)
                        desc = "Completed"

            if success:
                cell["pinned"] = True
                if desc:
                    cell["narration"] = desc

            history.append(
                {
                    "prompt": prompt,
                    "success": success,
                    "description": desc,
                }
            )

        except Exception as e:
            logger.error("Autopilot step %d failed: %s", step + 1, e)
            history.append(
                {
                    "prompt": f"Step {step + 1}",
                    "success": False,
                    "description": str(e),
                }
            )

    # ── Auto-compile into a ready-to-share Report ────────────────
    pinned_blocks = [c for c in state.notebook_cells if c.get("pinned")]
    if pinned_blocks:
        try:
            from services.report_service import ReportService
            from services.storage_service import StorageService

            storage = StorageService(page)
            rep_service = ReportService(storage)
            dataset_label = state.active_project_dataset or "Dataset"
            rep_title = f"Autopilot: {dataset_label}"
            await rep_service.create_report(
                title=rep_title,
                dataset_name=dataset_label,
                blocks=pinned_blocks,
                description=f"Automated intelligence report generated by SpanInsight Autopilot for {dataset_label}.",
            )
            if page:
                show_snack(
                    page,
                    "📊 Autopilot completed! Report compiled in Reports tab.",
                    success=True,
                )
        except Exception as rep_err:
            logger.warning("Autopilot report compilation error: %s", rep_err)

    state.autopilot_running = False
    state.autopilot_progress = ""
