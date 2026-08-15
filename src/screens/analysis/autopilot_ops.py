"""AI prompt generation, dataset file loading, and autopilot engine handlers."""

from __future__ import annotations

import json
import logging
import os

import flet as ft

from core import tokens
from core.constants import COST_AUTOPILOT, COST_CUSTOM_PROMPT
from core.state import state

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
            page.snack_bar = ft.SnackBar(
                ft.Text("Connect to Colab first"),
                bgcolor=ft.Colors.ERROR,
            )
            page.snack_bar.open = True
            page.update()
        return

    set_is_generating(True)
    set_prompt_text("")

    try:
        if credits:
            ok, _ = await credits.spend(COST_CUSTOM_PROMPT)
            if not ok:
                if page:
                    page.snack_bar = ft.SnackBar(
                        ft.Text("Not enough credits"),
                        bgcolor=ft.Colors.ERROR,
                    )
                    page.snack_bar.open = True
                    page.update()
                return

        from services.ai import analysis as ai_service

        code = await ai_service.generate_code(prompt, schema_json)
        if not code:
            if page:
                page.snack_bar = ft.SnackBar(
                    ft.Text("AI couldn't generate code. Try rephrasing."),
                    bgcolor=ft.Colors.ERROR,
                )
                page.snack_bar.open = True
                page.update()
            return

        cell = add_cell_fn("code", code)
        cell["prompt"] = prompt
        set_is_generating(False)
        await run_cell_fn(cell["id"])

        # Auto-correct on error
        if cell.get("outputs"):
            last_out = cell["outputs"][-1]
            if last_out.get("output_type") == "error":
                error_text = "\n".join(last_out.get("traceback", []))
                corrected = await ai_service.generate_corrected_code(
                    prompt, code, error_text, schema_json
                )
                if corrected and corrected != code:
                    cell["source"] = corrected
                    cell["outputs"] = []
                    on_cell_change()
                    await run_cell_fn(cell["id"])

        # Concurrently generate AI executive narration and follow-up suggestions
        async def _narrate_and_suggest(c):
            import asyncio

            try:
                stdout_str = ""
                for out in c.get("outputs", []):
                    if out.get("output_type") == "stream":
                        stdout_str += out.get("text", "")
                    elif out.get("data", {}).get("text/plain"):
                        stdout_str += str(out["data"]["text/plain"])

                desc_task = ai_service.describe_result(
                    initial_desc=schema_json.get("description", "Dataset Analysis"),
                    res_data={"prompt": prompt, "code": code, "stdout": stdout_str},
                )
                sugg_task = ai_service.suggest(schema_json)
                narration, suggs = await asyncio.gather(desc_task, sugg_task)
                c["narration"] = narration
                c["suggestions"] = suggs
                on_cell_change()
            except Exception as ex:
                logger.warning("Post-execution narration failed: %s", ex)

        if page:
            page.run_task(_narrate_and_suggest, cell)

        # Refresh global suggestions
        if page and fetch_suggestions_fn:
            page.run_task(fetch_suggestions_fn)

    except Exception as e:
        logger.error("Prompt submission failed: %s", e)
        if page:
            page.snack_bar = ft.SnackBar(
                ft.Text(f"Error: {e}"), bgcolor=ft.Colors.ERROR
            )
            page.snack_bar.open = True
            page.update()
    finally:
        set_is_generating(False)


async def pick_and_upload_file_async(
    session_name: str,
    colab,
    page: ft.Page,
    add_cell_fn,
    run_cell_fn,
    fetch_suggestions_fn,
    set_schema_json,
    set_is_generating,
):
    """FilePicker dialog, upload to Colab /content/, generate load code, and extract schema."""
    if not session_name:
        if page:
            page.snack_bar = ft.SnackBar(
                ft.Text("Connect to Colab first"),
                bgcolor=ft.Colors.ERROR,
            )
            page.snack_bar.open = True
            page.update()
        return

    picker = page.file_picker
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

        # File size formatted string
        size_str = ""
        try:
            sz = os.path.getsize(picked.path)
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
            bgcolor=ft.Colors.with_opacity(0.12, ft.Colors.PRIMARY),
        )
        status_text = ft.Text(
            f"Uploading to Colab VM…{size_str}",
            size=tokens.FONT_XS,
            color=ft.Colors.ON_SURFACE_VARIANT,
        )
        upload_dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text(
                f"Importing {picked.name}",
                size=tokens.FONT_MD,
                weight=ft.FontWeight.W_600,
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
            from services.file_service import suggest_load_code, validate_file

            validate_file(picked.path)

            remote_path = f"/content/{picked.name}"
            await colab.upload(picked.path, remote_path, session_name)

            _update_status("Loading dataset & generating preview…")
            load_code = suggest_load_code(picked.name)
            cell = add_cell_fn("code", load_code)
            cell["prompt"] = f"Load Dataset: {picked.name}"
            set_is_generating(False)
            await run_cell_fn(cell["id"])

            _update_status("Analyzing schema & dataset statistics…")
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

            # Parse schema from silent execution output
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
                try:
                    parsed = json.loads(json_part)
                    from services.ai import analysis as ai_service

                    try:
                        parsed["description"] = await ai_service.describe_dataset(
                            parsed
                        )
                        parsed["suggestions"] = await ai_service.suggest(parsed)
                    except Exception as ai_err:
                        logger.debug("Initial AI schema description failed: %s", ai_err)
                    set_schema_json(parsed)
                    if page and fetch_suggestions_fn:
                        page.run_task(fetch_suggestions_fn)
                except Exception as ex:
                    logger.warning("Schema parsing failed: %s", ex)

            if page:
                page.snack_bar = ft.SnackBar(ft.Text(f"✅ Ready: {picked.name}"))
                page.snack_bar.open = True

        except Exception as e:
            logger.error("File import failed: %s", e)
            if page:
                page.snack_bar = ft.SnackBar(
                    ft.Text(f"Import failed: {e}"),
                    bgcolor=ft.Colors.ERROR,
                )
                page.snack_bar.open = True
        finally:
            if page:
                try:
                    page.pop_dialog()
                except Exception:
                    pass
            set_is_generating(False)


async def run_autopilot_async(
    session_name: str,
    schema_json: dict,
    credits,
    page: ft.Page,
    add_cell_fn,
    run_cell_fn,
):
    """Execute autonomous multi-step analytical autopilot."""
    if not session_name or not schema_json:
        if page:
            page.snack_bar = ft.SnackBar(
                ft.Text("Upload a dataset first to use Autopilot"),
                bgcolor=ft.Colors.ERROR,
            )
            page.snack_bar.open = True
            page.update()
        return

    if credits:
        ok, _ = await credits.spend(COST_AUTOPILOT)
        if not ok:
            if page:
                page.snack_bar = ft.SnackBar(
                    ft.Text("Not enough credits for Autopilot"),
                    bgcolor=ft.Colors.ERROR,
                )
                page.snack_bar.open = True
                page.update()
            return

    state.autopilot_running = True
    state.autopilot_cancelled = False
    state.autopilot_progress = "Starting autopilot..."
    max_steps = 8

    from services.ai import analysis as ai_service

    history = []
    try:
        initial_desc = await ai_service.describe_dataset(schema_json)
    except Exception:
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

            code = await ai_service.generate_code(
                prompt,
                schema_json,
                analysis_context="\n".join(h.get("prompt", "") for h in history),
            )
            if not code:
                continue

            cell = add_cell_fn("code", code)
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
                    except Exception:
                        desc = "Completed"

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

    state.autopilot_running = False
    state.autopilot_progress = ""
