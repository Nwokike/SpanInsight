import asyncio
import logging
import uuid

import flet as ft
import httpx

from components.credit_badge import show_credits_dialog
from core.constants import COST_CUSTOM_PROMPT, COST_SUGGEST
from core.state import state
from core.utils import figure_to_png_bytes
from services import ai as ai_service
from services import sandbox

from .base import build_analysis_context, show_error

logger = logging.getLogger(__name__)


async def execute_pending_blocks(view_state):
    """
    Delta Sync Engine: Scans for blocks downloaded from collaborators that
    need to be executed locally to generate charts without transferring heavy images.
    """
    if state.current_df is None:
        return

    # Check if any blocks need execution before taking the lock
    needs_run = any(b.get("needs_execution") for b in state.analysis_blocks)
    if not needs_run:
        return

    if view_state.analysis_lock.locked():
        return

    async with view_state.analysis_lock:
        state.is_analyzing = True
        view_state.rebuild()

        executed_count = 0

        for block in state.analysis_blocks:
            if not block.get("needs_execution"):
                continue

            code = block.get("code", "")
            if not code:
                block["needs_execution"] = False
                continue

            try:
                res = await sandbox.execute_code_async(code, state.current_df)
                if res["success"]:
                    raw_figure = res.get("figure")
                    figure_png = None
                    if raw_figure:
                        try:
                            figure_png = await asyncio.to_thread(
                                figure_to_png_bytes, raw_figure
                            )
                        except Exception:
                            pass
                        res["figure"] = None  # Free C++ memory reference

                    block["figure_png"] = figure_png
                    block["stdout"] = res.get("stdout", "")
                    block["result"] = res.get("result", "")
                    block["failed"] = False

                    if res.get("modified"):
                        state.dataset_modified = True
                        if res.get("new_df") is not None:
                            state.current_df = res["new_df"]
                            state.current_df_columns = list(state.current_df.columns)
                            state.current_df_rows = len(state.current_df)
                            from services import file_service

                            state.current_df_summary = file_service.get_data_summary(
                                state.current_df
                            )
                else:
                    block["failed"] = True
                    block["description"] = (
                        f"Collaborator code failed locally: {res.get('error', 'Unknown error')}"
                    )
            except Exception as e:
                logger.error(
                    "Failed to execute pending block %s: %s", block.get("id"), e
                )
                block["failed"] = True
            finally:
                block["needs_execution"] = False
                executed_count += 1
                view_state.rebuild()

        state.is_analyzing = False
        view_state.rebuild()
        if executed_count > 0:
            logger.info(
                "Delta Sync: Successfully rendered %d collaborator blocks locally.",
                executed_count,
            )


async def on_suggestion_selected(
    view_state, prompt: str, is_autopilot: bool = False, is_custom: bool = False
):
    if state.current_df is None:
        return

    if view_state.analysis_lock.locked():
        return

    async with view_state.analysis_lock:
        state.is_analyzing = True
        view_state.rebuild()

        tx_id = None
        try:
            ctx = build_analysis_context()

            try:
                code = await ai_service.generate_code(
                    prompt, state.current_df_summary, analysis_context=ctx
                )
            except httpx.HTTPError as net_err:
                logger.warning("Offline network error: %s", net_err)
                show_error(
                    view_state,
                    "⚠️ Connection failed. You are currently offline. Please check your internet connection and try again.",
                )
                return

            if not code:
                show_error(
                    view_state, "AI failed to generate code. Try a different prompt."
                )
                return

            if not is_autopilot:
                cost = COST_CUSTOM_PROMPT if is_custom else COST_SUGGEST
                tx_id = await view_state.credit_service.reserve(cost)
                if not tx_id:
                    show_credits_dialog(view_state.page, view_state.credit_service)
                    return

            max_retries = 2
            retry_count = 0
            current_code = code
            result = None

            while retry_count <= max_retries:
                result = await sandbox.execute_code_async(
                    current_code, state.current_df
                )
                if result["success"]:
                    if result.get("modified"):
                        state.dataset_modified = True
                        if result.get("new_df") is not None:
                            state.current_df = result["new_df"]
                            state.current_df_columns = list(state.current_df.columns)
                            state.current_df_rows = len(state.current_df)
                            from services import file_service

                            state.current_df_summary = file_service.get_data_summary(
                                state.current_df
                            )
                    break

                retry_count += 1
                if retry_count <= max_retries:
                    logger.info(
                        "Execution failed (attempt %d/%d), AI self-healing: %s",
                        retry_count,
                        max_retries,
                        result["error"][:120],
                    )
                    try:
                        corrected = await ai_service.generate_corrected_code(
                            prompt,
                            current_code,
                            result["error"],
                            state.current_df_summary,
                        )
                        if corrected:
                            current_code = corrected
                            continue
                        else:
                            break
                    except httpx.ConnectError, httpx.TimeoutException:
                        break

            if not result or not result["success"]:
                if not is_autopilot and tx_id:
                    await view_state.credit_service.rollback(tx_id)
                block = {
                    "id": "blk_" + str(uuid.uuid4())[:8],
                    "type": "analysis",
                    "prompt": prompt,
                    "code": current_code,
                    "figure": None,
                    "figure_png": None,
                    "stdout": result.get("stdout", "") if result else "",
                    "result": "",
                    "description": f"Execution failed after {max_retries} self-heal attempts: {result.get('error', 'Unknown Error') if result else 'Code Generation Error'}",
                    "suggestions": [],
                    "pinned": False,
                    "failed": True,
                    "is_synced": False,
                }
                state.analysis_blocks.append(block)
                view_state.rebuild()

                # Push block in background if online
                from services.project_service import ProjectService

                asyncio.create_task(
                    ProjectService(
                        view_state.page, view_state.credit_service._storage
                    ).sync_project(state.active_project_id)
                )
                return

            if not is_autopilot and tx_id:
                await view_state.credit_service.commit(tx_id)

            figure_png = None
            raw_figure = result.get("figure")
            if raw_figure:
                try:
                    figure_png = await asyncio.to_thread(
                        figure_to_png_bytes, raw_figure
                    )
                except Exception:
                    pass
                result["figure"] = None  # Free C++ memory reference
                raw_figure = None

            block = {
                "id": "blk_" + str(uuid.uuid4())[:8],
                "type": "analysis",
                "prompt": prompt,
                "code": current_code,
                "figure": None,
                "figure_png": figure_png,
                "stdout": result.get("stdout", ""),
                "result": result.get("result", ""),
                "description": "Generating insight...",
                "suggestions": [],
                "pinned": is_autopilot,
                "failed": False,
                "is_synced": False,
            }

            state.analysis_blocks.append(block)
            wrapped_block = state.analysis_blocks[-1]
            view_state.rebuild()

            async def load_block_ai(b):
                try:
                    block0_desc = (
                        state.analysis_blocks[0]["description"]
                        if state.analysis_blocks
                        else ""
                    )
                    res_data = {
                        "prompt": b["prompt"],
                        "code": b["code"],
                        "stdout": b["stdout"],
                        "result": str(b["result"]),
                    }

                    ctx = build_analysis_context()

                    # Run AI calls concurrently for extreme speed
                    desc_task = ai_service.describe_result(block0_desc, res_data)
                    sugg_task = ai_service.suggest(
                        state.current_df_summary,
                        initial_description=block0_desc,
                        analysis_context=ctx,
                    )

                    description, suggestions = await asyncio.gather(
                        desc_task, sugg_task
                    )

                    b["description"] = description
                    b["suggestions"] = suggestions
                    state.suggestions = suggestions

                    if is_autopilot:
                        state.charts.append(
                            {
                                "prompt": b["prompt"],
                                "figure": None,
                                "figure_png": b.get("figure_png"),
                                "description": description,
                            }
                        )

                    view_state.rebuild()

                    from services.project_service import ProjectService

                    async def _safe_sync():
                        try:
                            await ProjectService(
                                view_state.page, view_state.credit_service._storage
                            ).sync_project(state.active_project_id)
                        except Exception as sync_err:
                            logger.warning("Background sync failed: %s", sync_err)

                    asyncio.create_task(_safe_sync())

                except Exception as e:
                    logger.error("Block AI load failed: %s", e)

            await load_block_ai(wrapped_block)

        except httpx.HTTPError as net_err:
            logger.warning("Connection failure: %s", net_err)
            show_error(
                view_state,
                "⚠️ Connection failed. You are currently offline. Please check your internet connection and try again.",
            )
            if not is_autopilot and tx_id:
                await view_state.credit_service.rollback(tx_id)
        except Exception as err:
            show_error(view_state, f"Analysis failed: {err}")
            logger.exception("Analysis error")
        finally:
            state.is_analyzing = False
            try:
                state.credits_remaining = await view_state.credit_service.get_balance()
            except Exception:
                pass
            view_state.rebuild()


async def on_custom_prompt(view_state, e):
    if not view_state.custom_prompt_field.current:
        return
    prompt = view_state.custom_prompt_field.current.value.strip()
    if not prompt:
        return

    view_state.custom_prompt_field.current.value = ""
    view_state.page.update()
    await on_suggestion_selected(view_state, prompt, is_custom=True)


async def _handle_voice_auto_stop(page: ft.Page, ui_state, result):
    ui_state.is_recording["value"] = False
    ui_state.is_transcribing["value"] = True
    ui_state.rebuild()
    if result:
        audio_bytes, mime = result
        try:
            transcript = await ai_service.transcribe_audio(audio_bytes, mime)
            if transcript and not transcript.startswith("["):
                ui_state.ai_prompt_text["value"] = transcript
        except httpx.ConnectError, httpx.TimeoutException:
            logger.warning("Offline network error during voice transcription.")
        except Exception as ex:
            logger.error("Voice transcription failed: %s", ex)
    ui_state.is_transcribing["value"] = False
    ui_state.rebuild()


async def _handle_auto_stop(view_state, result):
    view_state.is_recording["value"] = False
    view_state.is_transcribing["value"] = True
    view_state.rebuild()
    if result:
        audio_bytes, mime_type = result
        try:
            transcript = await ai_service.transcribe_audio(audio_bytes, mime_type)
            if (
                transcript
                and not transcript.startswith("[")
                and view_state.custom_prompt_field.current
            ):
                view_state.custom_prompt_field.current.value = transcript
                view_state.page.update()
        except httpx.ConnectError, httpx.TimeoutException:
            show_error(
                view_state, "⚠️ Voice transcription failed. You are currently offline."
            )
        except Exception as ex:
            logger.error("Voice transcription error: %s", ex)
    view_state.is_transcribing["value"] = False
    view_state.rebuild()


async def on_voice_toggle(view_state, e):
    if view_state.is_recording["value"]:
        result = await view_state.audio_svc.stop_recording()
        view_state.is_recording["value"] = False
        view_state.is_transcribing["value"] = True
        view_state.rebuild()
        if result:
            audio_bytes, mime_type = result
            try:
                transcript = await ai_service.transcribe_audio(audio_bytes, mime_type)
                if (
                    transcript
                    and not transcript.startswith("[")
                    and view_state.custom_prompt_field.current
                ):
                    view_state.custom_prompt_field.current.value = transcript
                    view_state.page.update()
            except httpx.ConnectError, httpx.TimeoutException:
                show_error(
                    view_state,
                    "⚠️ Voice transcription failed. You are currently offline.",
                )
            except Exception as ex:
                logger.error("Voice transcription error: %s", ex)
        view_state.is_transcribing["value"] = False
        view_state.rebuild()
    else:
        started = await view_state.audio_svc.start_recording(
            on_auto_stop=lambda res: view_state.page.run_task(
                _handle_auto_stop, view_state, res
            )
        )
        if started:
            view_state.is_recording["value"] = True
            view_state.recording_time["value"] = 0
            view_state.rebuild()

    while view_state.is_recording["value"]:
        await asyncio.sleep(1)
        if view_state.is_recording["value"]:
            view_state.recording_time["value"] += 1
            if view_state.recording_timer.current:
                view_state.recording_timer.current.value = (
                    f"00:{view_state.recording_time['value']:02d} / 01:00"
                )
                view_state.page.update(view_state.recording_timer.current)
    view_state.is_recording["value"] = False


async def on_run_code(view_state, code: str):
    """Execute raw user code directly (no AI generation)."""
    if not code or view_state.analysis_lock.locked():
        return

    async with view_state.analysis_lock:
        state.is_analyzing = True
        view_state.rebuild()

        try:
            result = await sandbox.execute_code_async(code, state.current_df)

            figure_png = None
            if result["success"]:
                if result.get("modified"):
                    state.dataset_modified = True
                    if result.get("new_df") is not None:
                        state.current_df = result["new_df"]
                        state.current_df_columns = list(state.current_df.columns)
                        state.current_df_rows = len(state.current_df)
                        from services import file_service

                        state.current_df_summary = file_service.get_data_summary(
                            state.current_df
                        )
                raw_figure = result.get("figure")
                if raw_figure:
                    try:
                        figure_png = await asyncio.to_thread(
                            figure_to_png_bytes, raw_figure
                        )
                    except Exception:
                        pass
                    result["figure"] = None

            block = {
                "id": "blk_" + str(uuid.uuid4())[:8],
                "type": "analysis",
                "prompt": "# User Code",
                "code": code,
                "figure": None,
                "figure_png": figure_png,
                "stdout": result.get("stdout", ""),
                "result": result.get("result", ""),
                "description": "",
                "suggestions": [],
                "pinned": False,
                "failed": not result["success"],
                "is_synced": False,
            }

            if not result["success"]:
                block["description"] = (
                    f"Execution failed: {result.get('error', 'Unknown error')}"
                )

            state.analysis_blocks.append(block)
            view_state.rebuild()

            if result["success"]:
                try:
                    balance = await view_state.credit_service.get_balance()
                except Exception:
                    balance = 0

                if balance > 0:
                    tx_id = await view_state.credit_service.reserve(COST_SUGGEST)
                    if tx_id:
                        try:
                            ctx = build_analysis_context()
                            block0_desc = (
                                state.analysis_blocks[0]["description"]
                                if state.analysis_blocks
                                else ""
                            )
                            res_data = {
                                "prompt": "# User Code",
                                "code": code,
                                "stdout": block["stdout"],
                                "result": str(block["result"]),
                            }
                            description, suggestions = await asyncio.gather(
                                ai_service.describe_result(block0_desc, res_data),
                                ai_service.suggest(
                                    state.current_df_summary,
                                    initial_description=block0_desc,
                                    analysis_context=ctx,
                                ),
                            )
                            block["description"] = description
                            block["suggestions"] = suggestions
                            state.suggestions = suggestions
                            await view_state.credit_service.commit(tx_id)
                        except Exception:
                            await view_state.credit_service.rollback(tx_id)
                            block["description"] = (
                                "Code executed. Add credits to unlock AI-powered insights."
                            )
                        else:
                            from services.project_service import ProjectService

                            asyncio.create_task(
                                ProjectService(
                                    view_state.page,
                                    view_state.credit_service._storage,
                                ).sync_project(state.active_project_id)
                            )
                    else:
                        block["description"] = (
                            "Code executed. Add credits to unlock AI-powered insights."
                        )
                else:
                    block["description"] = (
                        "Code executed. Add credits to unlock AI-powered insights."
                    )
                view_state.rebuild()

        except Exception as err:
            from .base import show_error

            show_error(view_state, f"Execution failed: {err}")
            logger.exception("on_run_code error")
        finally:
            state.is_analyzing = False
            try:
                state.credits_remaining = await view_state.credit_service.get_balance()
            except Exception:
                pass
            view_state.rebuild()
