"""Colab connection, cell execution, and notebook export async handlers."""

from __future__ import annotations

import json
import logging
import time

import flet as ft

from components.notebook_cell.output import parse_outputs_to_controls
from core.constants import COLAB_DEFAULT_TIMEOUT
from core.state import state

logger = logging.getLogger("ColabHandlers")

_OUTPUT_THROTTLE_MS = 150


async def connect_colab_async(colab, page: ft.Page, set_is_connecting):
    """Start or verify Colab VM session."""
    set_is_connecting(True)
    try:
        auth_result = await colab.check_auth()
        if not auth_result.get("authenticated"):
            if page:
                page.snack_bar = ft.SnackBar(
                    ft.Text("Please sign in to Google Colab first."),
                    action="Sign In",
                )
                page.snack_bar.open = True
                page.update()
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
            page.snack_bar = ft.SnackBar(
                ft.Text(f"Connected — {state.session_hardware} session ready")
            )
            page.snack_bar.open = True
            page.update()

    except Exception as e:
        logger.error("Connect failed: %s", e)
        if page:
            page.snack_bar = ft.SnackBar(
                ft.Text(f"Connection failed: {e}"),
                bgcolor=ft.Colors.ERROR,
            )
            page.snack_bar.open = True
            page.update()
    finally:
        set_is_connecting(False)


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
    if not cell or not session_name:
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

    try:
        timeout = state.default_timeout or COLAB_DEFAULT_TIMEOUT
        outputs = await colab.exec_code(
            code=code,
            session_name=session_name,
            timeout=float(timeout),
            on_output=_on_output,
        )
        if outputs:
            cell["outputs"] = outputs if isinstance(outputs, list) else [outputs]
        elif output_buffer:
            cell["outputs"] = list(output_buffer)

    except Exception as e:
        err_msg = str(e)
        cell["outputs"] = [
            {
                "output_type": "error",
                "ename": type(e).__name__,
                "evalue": err_msg,
                "traceback": [err_msg],
            }
        ]
    finally:
        cell["is_running"] = False
        set_is_executing(False)
        _flush_output_to_ui(refs, cell, page)
        on_cell_change()

        # Trigger AI executive narration and suggestions for the completed cell
        if cell.get("outputs"):
            last_out = cell["outputs"][-1]
            if last_out.get("output_type") != "error":

                async def _post_exec_ai(c):
                    import asyncio

                    try:
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

                        res_data = {
                            "prompt": c.get("prompt") or c.get("source", ""),
                            "code": c.get("source", ""),
                            "stdout": stdout_str,
                            "result": result_str,
                        }
                        ctx = "\n".join(
                            cell_item.get("prompt") or cell_item.get("source", "")[:80]
                            for cell_item in state.notebook_cells
                            if cell_item.get("type") == "code"
                        )
                        schema = getattr(state, "active_schema_json", {}) or {}
                        desc_task = ai_service.describe_result(
                            "Dataset Analysis", res_data
                        )
                        sugg_task = ai_service.suggest(schema, analysis_context=ctx)
                        narration, suggs = await asyncio.gather(desc_task, sugg_task)
                        c["narration"] = narration
                        c["suggestions"] = suggs
                        state.suggestions = suggs
                        on_cell_change()
                    except Exception:
                        pass

                if page:
                    page.run_task(_post_exec_ai, cell)


def _flush_output_to_ui(refs_dict: dict, c: dict, page: ft.Page):
    """Helper to push updated cell outputs to ListView refs safely."""
    try:
        output_lv = refs_dict.get("output")
        output_panel = refs_dict.get("output_panel")
        if output_lv and output_lv.current:
            new_controls = parse_outputs_to_controls(c["outputs"])
            output_lv.current.controls = new_controls
        if output_panel and output_panel.current:
            output_panel.current.visible = True
        if page and page.loop:
            page.loop.call_soon_threadsafe(page.update)
    except Exception:
        pass


async def export_ipynb_async(page: ft.Page):
    """Convert state notebook cells to standard Jupyter Notebook format and save."""
    if not state.notebook_cells:
        return
    from services.ipynb_converter import cells_to_ipynb

    ipynb = cells_to_ipynb(state.notebook_cells)

    picker = page.file_picker
    path = await picker.save_file(
        file_name="spaninsight_notebook.ipynb",
        dialog_title="Export Notebook",
    )
    if path:
        try:
            import pathlib

            pathlib.Path(path).write_text(json.dumps(ipynb, indent=2))
            if page:
                page.snack_bar = ft.SnackBar(ft.Text(f"Exported to {path}"))
                page.snack_bar.open = True
                page.update()
        except Exception as e:
            if page:
                page.snack_bar = ft.SnackBar(
                    ft.Text(f"Export failed: {e}"),
                    bgcolor=ft.Colors.ERROR,
                )
                page.snack_bar.open = True
                page.update()
