"""Cell code execution runner, output streaming, and AI self-healing."""

from __future__ import annotations

import asyncio
import json
import logging
import time

import flet as ft

from components.notebook_cell.output import parse_cell_outputs
from core.constants import COLAB_DEFAULT_TIMEOUT
from core.state import state
from core.utils import build_analysis_context, show_snack
from services import ai as ai_service
from services.colab.introspection import (
    build_result_serialization_code,
    parse_result_from_outputs,
)
from services.colab.output_utils import extract_error_text

from .colab_connection import (
    connect_colab_async,
    ensure_active_dataset_in_kernel,
    recover_session_async,
    session_expired,
)

logger = logging.getLogger("ExecutionRunner")

_OUTPUT_THROTTLE_MS = 400


def flush_output_to_ui(refs_dict: dict, c: dict, page: ft.Page):
    """Push updated cell outputs to the cell's own refs."""
    try:
        output_lv = refs_dict.get("output")
        output_panel = refs_dict.get("output_panel")

        def _apply():
            try:
                if output_lv and output_lv.current:
                    output_lv.current.controls = parse_cell_outputs(c)
                    output_lv.current.update()
                if output_panel and output_panel.current:
                    output_panel.current.visible = True
                    output_panel.current.update()
            except Exception:
                logger.debug("Cell output patch skipped", exc_info=True)

        if page and page.loop:
            page.loop.call_soon_threadsafe(_apply)
        else:
            _apply()
    except Exception:
        logger.debug("Cell output flush skipped", exc_info=True)


async def run_cell_async(
    cell_id: str,
    session_name: str,
    colab,
    page: ft.Page,
    cell_refs_map,
    set_is_executing,
    on_cell_change,
):
    """Execute a single notebook cell and stream outputs to the UI."""
    cell = next((c for c in state.notebook_cells if c["id"] == cell_id), None)
    if not cell:
        return

    active_sess = state.active_session_name or session_name
    if not active_sess:
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
                    "Colab is not connected. Please connect to a session first.",
                    error=True,
                )
            return

    code = cell.get("source", "").strip()
    if not code:
        return

    cell["is_running"] = True
    cell["outputs"] = []
    set_is_executing(True)
    on_cell_change()

    refs = cell_refs_map.current.get(cell_id, {})
    last_update = [0.0]
    output_buffer = []

    def _on_output(text: str):
        output_buffer.append({"output_type": "stream", "name": "stdout", "text": text})
        now = time.monotonic()
        if now - last_update[0] < _OUTPUT_THROTTLE_MS / 1000:
            return
        last_update[0] = now

        cell["outputs"] = list(output_buffer)
        flush_output_to_ui(refs, cell, page)

    async def _exec_once(sess: str):
        output_buffer.clear()
        src = cell.get("source", "").strip()
        timeout = state.default_timeout or COLAB_DEFAULT_TIMEOUT
        if cell.get("is_initial_load"):
            timeout = max(float(timeout), 300.0)
        outputs = await colab.exec_code(
            code=src,
            session_name=sess,
            timeout=float(timeout),
            on_output=_on_output,
        )
        if outputs:
            cell["outputs"] = outputs if isinstance(outputs, list) else [outputs]
        elif output_buffer:
            cell["outputs"] = list(output_buffer)

    def _has_error() -> bool:
        return extract_error_text(cell.get("outputs", [])) is not None

    async def _serialize_result(sess: str):
        """Silently serialize the kernel's `result` variable for native rendering."""
        try:
            ser_outputs = await colab.exec_code(
                build_result_serialization_code(),
                session_name=sess,
                timeout=15.0,
            )
            structured = parse_result_from_outputs(ser_outputs)
            if structured:
                cell["structured_result"] = structured
        except Exception as ser_ex:
            logger.warning("Structured result serialization failed: %s", ser_ex)

    async def _heal(attempt: int) -> bool:
        """Ask the AI to correct the failing code."""
        state.analysis_stage = 6
        state.analysis_stage_text = (
            f"🩹 AI self-healing code execution (attempt {attempt + 1}/2)…"
        )
        state.autopilot_progress = f"🩹 Self-healing code (attempt {attempt + 1}/2)…"
        if page:
            show_snack(
                page,
                f"🩹 AI self-healing code execution (attempt {attempt + 1})…",
                duration=2500,
            )

        error_text = extract_error_text(cell.get("outputs", [])) or "Unknown error"
        prompt_desc = cell.get("prompt") or cell.get("source", "")
        try:
            corrected = await ai_service.generate_corrected_code(
                prompt_desc,
                cell.get("source", ""),
                error_text,
                state.active_schema_json or {},
            )
        except Exception as ex:
            logger.warning("Self-healing code generation failed: %s", ex)
            return False
        if not corrected or corrected.strip() == cell.get("source", "").strip():
            return False
        cell["source"] = corrected
        cell["outputs"] = []
        output_buffer.clear()
        cell["heal_count"] = attempt + 1
        on_cell_change()
        return True

    MAX_HEAL_ATTEMPTS = 2
    can_heal = bool(cell.get("prompt"))
    session_used = active_sess

    try:
        heal_attempt = 0
        while True:
            try:
                state.analysis_stage = 4
                state.analysis_stage_text = "Executing in Colab kernel…"
                await _exec_once(session_used)
            except Exception as exec_err:
                if not session_expired(str(exec_err)):
                    raise
                cell["outputs"] = [
                    {
                        "output_type": "stream",
                        "name": "stdout",
                        "text": "🔄 Colab session reset - re-attaching workspace & dataset…",
                    }
                ]
                flush_output_to_ui(refs, cell, page)
                await recover_session_async(colab, page)
                session_used = state.active_session_name or session_name
                await ensure_active_dataset_in_kernel(colab, session_used)
                cell["outputs"] = []
                output_buffer.clear()
                continue

            if not _has_error():
                await _serialize_result(session_used)
                cell["failed"] = False
                break
            if not can_heal or heal_attempt >= MAX_HEAL_ATTEMPTS:
                cell["failed"] = True
                break
            if not await _heal(heal_attempt):
                cell["failed"] = True
                break
            heal_attempt += 1
    except Exception as e:
        err_msg = str(e)
        cell["outputs"] = [
            {
                "output_type": "error",
                "ename": type(e).__name__,
                "evalue": err_msg,
                "traceback": [f"{type(e).__name__}: {err_msg}"],
            }
        ]
        cell["failed"] = True
        flush_output_to_ui(refs, cell, page)
    finally:
        set_is_executing(False)
        cell["is_running"] = False
        on_cell_change()

        try:
            if refs.get("play_btn") and refs["play_btn"].current:
                refs["play_btn"].current.disabled = False
                refs["play_btn"].current.update()
            if refs.get("stop_row") and refs["stop_row"].current:
                refs["stop_row"].current.visible = False
                refs["stop_row"].current.update()
        except Exception:
            pass

        if not cell.get("failed", False):
            src_stripped = cell.get("source", "").strip()
            prompt_str = str(cell.get("prompt", ""))
            is_load_cell = (
                cell.get("skip_narration", False)
                or prompt_str.startswith("Load Dataset:")
                or cell.get("is_initial_load", False)
                or src_stripped.startswith(
                    "import pandas as pd\nimport numpy as np\n\ndf = "
                )
                or (
                    src_stripped.startswith("import pandas as pd")
                    and "read_csv(" in src_stripped
                    and len(src_stripped.splitlines()) <= 5
                )
            )

            if not is_load_cell:

                async def _post_exec_ai(c: dict):
                    try:
                        state.analysis_stage = 5
                        state.analysis_stage_text = (
                            "Compiling executive summary & takeaways…"
                        )
                        stdout_str = ""
                        result_str = ""
                        for out in c.get("outputs", []):
                            otype = out.get("output_type") or out.get("type", "")
                            if otype == "stream":
                                stdout_str += out.get("text", "")
                            elif otype in ("execute_result", "display_data"):
                                data = out.get("data", {})
                                if "text/plain" in data:
                                    result_str += str(data["text/plain"])

                        structured = c.get("structured_result")
                        if structured:
                            result_str += (
                                "\n" + json.dumps(structured, default=str)[:2000]
                            )

                        res_data = {
                            "prompt": c.get("prompt") or c.get("source", ""),
                            "code": c.get("source", ""),
                            "stdout": stdout_str[:4000],
                            "result": result_str[:4000],
                        }
                        ctx = build_analysis_context(state.notebook_cells)
                        schema = state.active_schema_json or {}
                        desc_task = ai_service.describe_result(
                            schema.get("description", "Dataset Analysis"), res_data
                        )
                        sugg_task = ai_service.suggest(schema, analysis_context=ctx)
                        narration, suggs = await asyncio.gather(desc_task, sugg_task)
                        c["narration"] = narration
                        c["suggestions"] = suggs
                        state.suggestions = suggs
                        try:
                            on_cell_change()
                        except Exception:
                            pass
                    except Exception as ai_ex:
                        logger.warning("Post-execution narration failed: %s", ai_ex)
                    finally:
                        state.analysis_stage = 0
                        state.analysis_stage_text = ""
                        state.is_analyzing = False

                if page:
                    page.run_task(_post_exec_ai, cell)
                else:
                    state.analysis_stage = 0
                    state.analysis_stage_text = ""
                    state.is_analyzing = False
        else:
            state.analysis_stage = 0
            state.analysis_stage_text = ""
            state.is_analyzing = False
