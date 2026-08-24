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
    colab=None,
):
    """Handle natural-language AI query, generate Python, and execute."""
    if not prompt.strip():
        return

    from screens.analysis.colab_connection import (
        connect_colab_async,
        ensure_active_dataset_in_kernel,
    )

    # 1. Guarantee a live Colab connection before spending credits or generating code
    active_sess = state.active_session_name or session_name
    if not active_sess or not state.colab_connected:
        if colab:
            if page:
                show_snack(page, "🔄 Connecting to Colab session first…", duration=2500)
            await connect_colab_async(colab, page, lambda _: None)
            active_sess = state.active_session_name
            if active_sess:
                await ensure_active_dataset_in_kernel(colab, active_sess)
        if not active_sess:
            if page:
                show_snack(
                    page,
                    "Colab is not connected. Please connect to a session in the header first.",
                    error=True,
                )
            return

    set_is_generating(True)
    state.is_analyzing = True
    state.analysis_stage = 2
    state.analysis_stage_text = "Planning approach…"
    set_prompt_text("")

    def _cell_res_data(cell: dict) -> dict:
        """Real execution artifacts for verification (mirrors _post_exec_ai caps)."""
        stdout = "".join(
            o.get("text", "")
            for o in cell.get("outputs", [])
            if isinstance(o, dict) and o.get("output_type") == "stream"
        )
        result_str = ""
        for o in cell.get("outputs", []):
            data = o.get("data", {}) if isinstance(o, dict) else {}
            if "text/plain" in data:
                result_str = str(data["text/plain"])
                break
        return {
            "prompt": cell.get("prompt", ""),
            "code": cell.get("source", ""),
            "stdout": stdout[:4000],
            "result": result_str[:4000],
            "structured_result": cell.get("structured_result"),
        }

    try:
        if credits:
            ok, _ = await credits.spend(COST_CUSTOM_PROMPT)
            if not ok:
                if page:
                    show_snack(page, "Not enough credits", error=True)
                return

        from core.utils import build_analysis_context
        from services.ai import analysis as ai_service

        # ── Agent pre-plan: decompose the question into 1-3 steps ──
        try:
            plan = await ai_service.plan_insight_approach(prompt, schema_json)
        except Exception as plan_ex:
            logger.warning("Approach planning failed, single-step: %s", plan_ex)
            plan = {"steps": [prompt]}
        steps = plan.get("steps") or [prompt]
        logger.info("Agent plan (%d steps): %s", len(steps), steps)

        schema_desc = (
            str(schema_json.get("description", ""))
            if isinstance(schema_json, dict)
            else ""
        )
        analysis_context = build_analysis_context(state.notebook_cells)

        final_cell = None
        final_verdict = None
        gaps: list[str] = []
        MAX_STEPS = min(len(steps), 3)

        for i, step in enumerate(steps[:MAX_STEPS]):
            state.analysis_stage = 2
            state.analysis_stage_text = f"Step {i + 1}/{MAX_STEPS}: {step[:70]}"

            meta = await ai_service.generate_code_meta(
                step, schema_json, analysis_context=analysis_context
            )
            code = meta.get("code", "")
            if not code:
                continue

            state.analysis_stage = 3
            state.analysis_stage_text = "Synthesizing specialized Python code…"

            cell = add_cell_fn("code", code)
            cell["prompt"] = prompt
            cell["step"] = step
            cell["thought"] = meta.get("thought", "")
            cell["thought_duration"] = meta.get("duration", 0.0)
            cell["model"] = meta.get("model", "")

            state.analysis_stage = 4
            state.analysis_stage_text = "Executing in Colab kernel & rendering visuals…"
            await run_cell_fn(cell["id"])
            final_cell = cell

            if cell.get("failed"):
                gaps = ["Execution failed even after self-healing."]
                analysis_context = (analysis_context + "\n" + step)[-2500:]
                continue

            # ── Verify against the user's literal question ──
            state.analysis_stage = 7
            state.analysis_stage_text = "Verifying against your data…"
            verdict = await ai_service.verify_result(
                prompt, schema_desc, _cell_res_data(cell)
            )
            cell["verified"] = bool(verdict.get("verified"))
            cell["key_numbers"] = verdict.get("key_numbers", [])

            if verdict.get("satisfied") or i == MAX_STEPS - 1:
                final_verdict = verdict
                if verdict.get("answer"):
                    cell["narration"] = verdict["answer"]
                cell["answer_gaps"] = (
                    [] if verdict.get("satisfied") else gaps or verdict.get("gaps", [])
                )
                cell["agent_answered"] = True
                break
            gaps = verdict.get("gaps") or []
            analysis_context = (analysis_context + "\n" + step)[-2500:]

        if final_cell is not None and not final_cell.get("agent_answered"):
            # Degraded path (verify unavailable / failed execution): the normal
            # post-exec narration from run_cell_async stands as-is.
            final_cell["answer_gaps"] = gaps

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
        state.analysis_stage = 0
        state.analysis_stage_text = ""
        state.is_analyzing = False
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
    state.autopilot_progress = "Initializing Autopilot intelligence…"
    state.autopilot_steps = []
    max_steps = 8

    from services.ai import analysis as ai_service

    history = []
    try:
        initial_desc = await ai_service.describe_dataset(schema_json)
    except Exception as ex:
        logger.warning("Autopilot initial describe failed: %s", ex)
        initial_desc = "Dataset loaded"

    import time

    start_autopilot_time = time.monotonic()

    for step in range(max_steps):
        if state.autopilot_cancelled:
            state.autopilot_progress = "Autopilot cancelled"
            if state.autopilot_steps:
                state.autopilot_steps[-1]["status"] = "pending"
            break

        step_start = time.monotonic()
        state.autopilot_progress = (
            f"Step {step + 1}/{max_steps}: Planning next insight…"
        )

        try:
            plan = await ai_service.plan_next_step(schema_json, initial_desc, history)
            if plan.get("is_complete"):
                state.autopilot_progress = (
                    f"Done - {plan.get('reason', 'Analysis complete')}"
                )
                break

            prompt = plan.get("prompt", "")
            if not prompt:
                break

            step_entry = {
                "text": f"Step {step + 1}: {prompt}",
                "status": "running",
                "time": "",
            }
            state.autopilot_steps.append(step_entry)
            state.autopilot_progress = f"Step {step + 1}/{max_steps}: {prompt}"
            if page:
                try:
                    page.update()
                except Exception:
                    pass

            meta = await ai_service.generate_code_meta(
                prompt,
                schema_json,
                analysis_context="\n".join(h.get("prompt", "") for h in history),
            )
            code = meta.get("code", "")
            if not code:
                step_entry["status"] = "done"
                continue

            cell = add_cell_fn("code", code)
            cell["prompt"] = prompt
            cell["thought"] = meta.get("thought", "")
            cell["thought_duration"] = meta.get("duration", 0.0)
            cell["model"] = meta.get("model", "")
            # Autopilot narrates each step itself - skip per-cell post-exec AI
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

            step_duration = time.monotonic() - step_start
            step_entry["status"] = "done" if success else "pending"
            step_entry["time"] = f"{step_duration:.1f}s"
            if page:
                try:
                    page.update()
                except Exception:
                    pass

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
            state.autopilot_steps.append(
                {
                    "text": f"Executive report compiled ({len(pinned_blocks)} insights)",
                    "status": "done",
                    "time": f"{time.monotonic() - start_autopilot_time:.1f}s",
                }
            )
            if page:
                show_snack(
                    page,
                    "📊 Autopilot completed! Report compiled in Reports tab.",
                    success=True,
                )
        except Exception as rep_err:
            logger.warning("Autopilot report compilation error: %s", rep_err)

    # ── Interstitial Ad on Autopilot Completion (Mobile) ─────────────
    if page and page.platform in (ft.PagePlatform.ANDROID, ft.PagePlatform.IOS):
        try:
            from services.ad_service import get_ad_service

            await get_ad_service(page).show_interstitial()
        except Exception as ad_err:
            logger.warning("Autopilot completion Interstitial failed: %s", ad_err)

    state.autopilot_running = False
    state.autopilot_progress = ""
    if page:
        try:
            page.update()
        except Exception:
            pass
