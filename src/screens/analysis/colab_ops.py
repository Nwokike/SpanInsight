"""Colab connection, cell execution, and notebook export async handlers."""

from __future__ import annotations

import json
import logging
import time

import flet as ft

from components.notebook_cell.output import parse_cell_outputs
from core.constants import COLAB_DEFAULT_TIMEOUT
from core.state import state

logger = logging.getLogger("ColabHandlers")

_OUTPUT_THROTTLE_MS = 400


async def connect_colab_async(colab, page: ft.Page, set_is_connecting):
    """Start or verify Colab VM session."""
    set_is_connecting(True)
    try:
        auth_result = await colab.check_auth()
        if not auth_result.get("authenticated"):
            if page:
                from core.utils import show_snack

                show_snack(page, "Please sign in to Google Colab first.", error=True)
            set_is_connecting(False)
            return

        state.colab_authenticated = True
        state.is_authenticated = True

        result = await colab.new_session(
            gpu=state.default_gpu or None,
            tpu=state.default_tpu or None,
            keep_alive=state.keep_alive_enabled,
        )
        state.active_session_name = result["name"]
        state.session_hardware = (
            "CPU"
            if result.get("accelerator") == "NONE"
            else result.get("accelerator", "CPU")
        )
        state.colab_connected = True

        from screens.analysis.bootstrap import setup_colab_environment

        is_dark = (
            state.theme_mode == ft.ThemeMode.DARK
            if hasattr(state, "theme_mode")
            else False
        )
        await setup_colab_environment(colab, state.active_session_name, is_dark=is_dark)

        if page:
            from core.utils import show_snack

            show_snack(
                page,
                f"Connected — {state.session_hardware} session ready",
                success=True,
            )

    except Exception as e:
        logger.error("Connect failed: %s", e)
        if page:
            from core.utils import show_snack

            show_snack(page, f"Connection failed: {e}", error=True)
    finally:
        set_is_connecting(False)


def _session_expired(msg: str) -> bool:
    lowered = msg.lower()
    return (
        "session has expired" in lowered
        or "session lost" in lowered
        or "kernel not found" in lowered
        or "timeout waiting for output" in lowered
        or "404" in lowered
        or "nameerror: name 'df' is not defined" in lowered
    )


async def ensure_active_dataset_in_kernel(colab, session_name: str) -> bool:
    """Ensure the active project's dataset is present on Colab and loaded into df."""
    if not session_name or not state.active_project_id:
        return False
    from services.dataset_cache import get_cached_path
    from services.file_service import suggest_load_code

    cached = get_cached_path(state.active_project_id)
    if cached and cached.exists():
        remote_path = f"/content/{cached.name}"
        try:
            await colab.upload(str(cached), remote_path, session_name)
            load_code = suggest_load_code(cached.name)
            await colab.exec_code(load_code, session_name=session_name)
            return True
        except Exception as ex:
            logger.warning("Failed to hydrate dataset in kernel: %s", ex)
            return False
    return False


async def recover_session_async(colab, page: ft.Page | None) -> None:
    """Rebuild a dead Colab session: new session → theme bootstrap → cached dataset reload.

    Called automatically when the kernel reports the session expired (404), so
    the user never silently loses their work — the locally cached dataset is
    re-uploaded and analysis continues on the fresh session.
    """
    await connect_colab_async(colab, page, lambda _v: None)
    if not state.active_session_name:
        raise RuntimeError("No active session after reconnect")

    try:
        await ensure_active_dataset_in_kernel(colab, state.active_session_name)
    except Exception as ex:
        logger.warning("Cached dataset reload after reconnect failed: %s", ex)


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

    # Guarantee an active, live Colab session
    active_sess = state.active_session_name or session_name
    if not active_sess:
        if colab:
            if page:
                from core.utils import show_snack

                show_snack(page, "🔄 Connecting to Colab session first…", duration=2500)
            await connect_colab_async(colab, page, lambda _: None)
            active_sess = state.active_session_name
            if active_sess:
                await ensure_active_dataset_in_kernel(colab, active_sess)
        if not active_sess:
            if page:
                from core.utils import show_snack

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
        _flush_output_to_ui(refs, cell, page)

    async def _exec_once(sess: str):
        output_buffer.clear()
        # Re-read source on every attempt so healed code actually executes
        src = cell.get("source", "").strip()
        timeout = state.default_timeout or COLAB_DEFAULT_TIMEOUT
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
        from services.colab.output_utils import extract_error_text

        return extract_error_text(cell.get("outputs", [])) is not None

    async def _serialize_result(sess: str):
        """Silently serialize the kernel's `result` variable for native rendering."""
        try:
            from services.colab.introspection import (
                build_result_serialization_code,
                parse_result_from_outputs,
            )

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
        """Ask the AI to correct the failing code (v1-style self-healing).

        Only cells that carry a `prompt` (AI-generated, dataset loads, autopilot
        steps) are auto-healed — hand-written Expert-mode code is never touched.
        """
        from services.ai import analysis as ai_service
        from services.colab.output_utils import extract_error_text

        state.analysis_stage = 6
        state.analysis_stage_text = (
            f"🩹 AI self-healing code execution (attempt {attempt + 1}/2)…"
        )
        state.autopilot_progress = f"🩹 Self-healing code (attempt {attempt + 1}/2)…"
        if page:
            from core.utils import show_snack

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
                if not _session_expired(str(exec_err)):
                    raise
                # Session died on Colab — auto-recover and retry instead of
                # dumping a dead-session traceback on the user.
                cell["outputs"] = [
                    {
                        "output_type": "stream",
                        "name": "stdout",
                        "text": "🔄 Colab session reset — re-attaching workspace & dataset…",
                    }
                ]
                _flush_output_to_ui(refs, cell, page)
                await recover_session_async(colab, page)
                session_used = state.active_session_name or session_name
                await ensure_active_dataset_in_kernel(colab, session_used)
                cell["outputs"] = []
                output_buffer.clear()
                continue  # session recovery does not consume a heal attempt

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
        _flush_output_to_ui(refs, cell, page)
    finally:
        set_is_executing(False)
        cell["is_running"] = False
        on_cell_change()

        # Re-enable the run button
        try:
            if refs.get("play_btn") and refs["play_btn"].current:
                refs["play_btn"].current.disabled = False
                refs["play_btn"].current.update()
            if refs.get("stop_row") and refs["stop_row"].current:
                refs["stop_row"].current.visible = False
                refs["stop_row"].current.update()
        except Exception:
            pass

        # Post-execution narration: generate AI description + next suggestions
        # ONLY if the cell succeeded and is an actual analysis cell.
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
                        import asyncio

                        from services.ai import analysis as ai_service

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
                            import json as _json

                            result_str += (
                                "\n" + _json.dumps(structured, default=str)[:2000]
                            )

                        res_data = {
                            "prompt": c.get("prompt") or c.get("source", ""),
                            "code": c.get("source", ""),
                            "stdout": stdout_str[:4000],
                            "result": result_str[:4000],
                        }
                        from core.utils import build_analysis_context

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


def _flush_output_to_ui(refs_dict: dict, c: dict, page: ft.Page):
    """Push updated cell outputs to the cell's own refs — NEVER a full page.update().

    Full-page updates fired every ~150ms while a kernel streams output used to
    saturate the event loop and freeze the whole UI (clicks stopped responding).
    Only the changed cell's subtree is patched here.
    """
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


async def export_ipynb_async(page: ft.Page):
    """Convert state notebook cells to standard .ipynb format and save to app storage.

    Written to FLET_APP_STORAGE_DATA (→ .flet/storage/data/ in dev,
    the app's private data directory on Android).
    """
    if not state.notebook_cells:
        return
    from services.ipynb_converter import cells_to_ipynb

    ipynb = cells_to_ipynb(state.notebook_cells)
    ipynb_text = json.dumps(ipynb, indent=2)

    try:
        import os
        import pathlib

        storage_data = os.getenv("FLET_APP_STORAGE_DATA")
        export_dir = (
            pathlib.Path(storage_data)
            if storage_data
            else pathlib.Path(".flet") / "storage" / "data"
        )
        export_dir.mkdir(parents=True, exist_ok=True)
        export_path = export_dir / "spaninsight_notebook.ipynb"
        export_path.write_text(ipynb_text, encoding="utf-8")

        if page:
            from core.utils import show_snack

            show_snack(
                page,
                "📓 Notebook exported to app storage",
                success=True,
                duration=4000,
            )
    except Exception as e:
        if page:
            from core.utils import show_snack

            show_snack(page, f"Export failed: {e}", error=True)
