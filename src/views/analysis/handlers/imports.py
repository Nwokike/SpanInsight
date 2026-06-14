import asyncio
import logging
import os
import uuid

from core.state import state
from core.constants import COST_SUGGEST
from core.utils import figure_to_png_bytes
from services import ai as ai_service, file_service, sandbox
from services.file_service import FileValidationError
from .base import show_error, show_success
from .autopilot import run_autopilot
from components.credit_badge import show_credits_dialog
from services import dataset_cache

logger = logging.getLogger(__name__)


async def process_file(view_state, file):
    if not file.path:
        show_error(view_state, "Could not access the selected file.")
        return

    # ── Recipe Re-execution / Link Dataset Mode ─────────────────────
    is_linking = bool(state.current_df_name) and state.current_df is None

    if is_linking:
        state.is_loading = True
        try:
            fsize = os.path.getsize(file.path)
        except OSError:
            fsize = 0
        view_state.loading_file_name["value"] = file.name
        view_state.loading_file_size["value"] = fsize
        view_state.rebuild()

        try:
            import matplotlib.pyplot as plt

            plt.close("all")
            df = await asyncio.to_thread(file_service.load_dataframe, file.path)

            # --- NEW: DATASET FINGERPRINT VALIDATION ---
            active_proj = state.user_projects.get(state.active_project_id, {})
            expected_fingerprint = active_proj.get("dataset_fingerprint")

            if expected_fingerprint:
                actual_fingerprint = await asyncio.to_thread(
                    file_service.generate_dataset_fingerprint, df
                )
                if actual_fingerprint != expected_fingerprint:
                    raise FileValidationError(
                        "Dataset mismatch. You must upload the exact file used to create this workspace."
                    )
            # -------------------------------------------

            state.set_dataframe(df, file.name)
            state.current_file_path = file.path

            # Cache the linked file locally for future auto-reload
            await asyncio.to_thread(
                dataset_cache.cache_file, state.active_project_id, file.path
            )

            state.current_df_summary = await asyncio.to_thread(
                file_service.get_data_summary, df
            )

            # Re-execute all code blocks sequentially in the background
            show_success(view_state, "Dataset linked! Applying analytical recipe...")

            for i, block in enumerate(state.analysis_blocks):
                if block.get("type") == "initial":
                    continue
                code = block.get("code", "")
                if code and not block.get("failed", False):
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
                        block["figure_png"] = figure_png or block.get("figure_png")
                        block["stdout"] = res.get("stdout", "")
                        block["result"] = res.get("result", "")
                        block["failed"] = False
                    else:
                        block["failed"] = True
                        block["description"] = (
                            f"Recipe execution failed: {res.get('error')}"
                        )

            show_success(view_state, "✅ Recipe applied successfully!")

        except Exception as err:
            show_error(view_state, f"Failed to link dataset: {err}")
            state.clear_data()
            logger.exception("Link dataset error")
        finally:
            state.is_loading = False
            view_state.rebuild()
        return

    state.is_loading = True
    try:
        fsize = os.path.getsize(file.path)
    except OSError:
        fsize = 0
    view_state.loading_file_name["value"] = file.name
    view_state.loading_file_size["value"] = fsize
    view_state.rebuild()

    try:
        import matplotlib.pyplot as plt

        plt.close("all")
        df = await asyncio.to_thread(file_service.load_dataframe, file.path)

        # --- NEW: GENERATE & STORE DATASET FINGERPRINT ---
        actual_fingerprint = await asyncio.to_thread(
            file_service.generate_dataset_fingerprint, df
        )
        if state.active_project_id and state.active_project_id in state.user_projects:
            state.user_projects[state.active_project_id]["dataset_fingerprint"] = (
                actual_fingerprint
            )
        # -------------------------------------------------

        state.set_dataframe(df, file.name)
        state.current_file_path = file.path

        # Cache the imported file locally for auto-reload on restart
        await asyncio.to_thread(
            dataset_cache.cache_file, state.active_project_id, file.path
        )

        state.current_df_summary = await asyncio.to_thread(
            file_service.get_data_summary, df
        )

        try:
            # PERFORMANCE FIX: Offload CPU-bound describe call to background thread to maintain UI responsiveness
            describe_data = await asyncio.to_thread(
                lambda: df.describe(include="all").round(2).fillna("")
            )
        except Exception:
            describe_data = None

        block0 = {
            "id": "blk_" + str(uuid.uuid4())[:8],
            "type": "initial",
            "code": "",
            "describe_data": describe_data,
            "description": "Analyzing dataset schema...",
            "suggestions": [],
            "pinned": False,
        }
        state.analysis_blocks.clear()
        state.analysis_blocks.append(block0)
        state.is_loading = False
        view_state.rebuild()

        async def load_initial_ai():
            try:
                success, _ = await view_state.credit_service.spend(COST_SUGGEST)
                if not success:
                    block0["description"] = (
                        "Dataset loaded. AI description unavailable (no credits)."
                    )
                    block0["suggestions"] = ai_service.fallback_suggestions()
                    state.suggestions = block0["suggestions"]
                    show_credits_dialog(view_state.page, view_state.credit_service)
                else:
                    # Execute describe and suggest concurrently to save up to 4+ seconds of startup latency
                    description, suggestions = await asyncio.gather(
                        ai_service.describe_dataset(state.current_df_summary),
                        ai_service.suggest(state.current_df_summary),
                    )
                    block0["description"] = description
                    block0["suggestions"] = suggestions
                    state.suggestions = suggestions

                state.credits_remaining = await view_state.credit_service.get_balance()
                view_state.rebuild()

                if getattr(state, "autopilot_enabled", False):
                    await run_autopilot(view_state)

            except Exception as e:
                logger.error("Initial AI load failed: %s", e)
                block0["description"] = (
                    f"Dataset loaded ({state.current_df_rows:,} rows, "
                    f"{len(state.current_df_columns)} columns). "
                    f"AI is offline — use custom prompts to analyze."
                )
                block0["suggestions"] = ai_service.fallback_suggestions()
                state.suggestions = block0["suggestions"]
                view_state.rebuild()

        view_state.page.run_task(load_initial_ai)

    except FileValidationError as err:
        show_error(view_state, str(err))
        state.clear_data()
    except Exception as err:
        show_error(view_state, f"Failed to load file: {err}")
        state.clear_data()
        logger.exception("File load error")
    finally:
        state.is_loading = False
        view_state.rebuild()


async def process_db_table(view_state, connection_url: str, table_name: str):
    state.is_loading = True
    view_state.loading_file_name["value"] = f"{table_name} [SQL]"
    view_state.loading_file_size["value"] = 0
    view_state.rebuild()

    await asyncio.sleep(0.1)

    try:
        import matplotlib.pyplot as plt
        from services.db_service import DatabaseService

        plt.close("all")
        df = await asyncio.to_thread(
            DatabaseService.load_table, connection_url, table_name
        )

        # --- NEW: GENERATE & STORE DATASET FINGERPRINT ---
        actual_fingerprint = await asyncio.to_thread(
            file_service.generate_dataset_fingerprint, df
        )
        if state.active_project_id and state.active_project_id in state.user_projects:
            state.user_projects[state.active_project_id]["dataset_fingerprint"] = (
                actual_fingerprint
            )
        # -------------------------------------------------

        state.set_dataframe(df, f"{table_name} (SQL)")
        state.current_file_path = f"sql://{table_name}"

        # For SQL imports, save a CSV copy to cache (no source file to copy)
        try:
            cache_dir = dataset_cache._DATASETS_DIR
            cache_dir.mkdir(parents=True, exist_ok=True)
            csv_path = cache_dir / f"{state.active_project_id}.csv"
            await asyncio.to_thread(lambda: df.to_csv(str(csv_path), index=False))
        except Exception as cache_err:
            logger.warning("Failed to cache SQL dataset: %s", cache_err)

        state.current_df_summary = await asyncio.to_thread(
            file_service.get_data_summary, df
        )

        try:
            # PERFORMANCE FIX: Offload CPU-bound describe call to background thread to maintain UI responsiveness
            describe_data = await asyncio.to_thread(
                lambda: df.describe(include="all").round(2).fillna("")
            )
        except Exception:
            describe_data = None

        block0 = {
            "id": "blk_" + str(uuid.uuid4())[:8],
            "type": "initial",
            "code": "",
            "describe_data": describe_data,
            "description": "Analyzing dataset schema...",
            "suggestions": [],
            "pinned": False,
        }
        state.analysis_blocks.clear()
        state.analysis_blocks.append(block0)
        state.is_loading = False
        view_state.rebuild()

        async def load_initial_ai():
            try:
                success, _ = await view_state.credit_service.spend(COST_SUGGEST)
                if not success:
                    block0["description"] = (
                        "Dataset loaded. AI description unavailable (no credits)."
                    )
                    block0["suggestions"] = ai_service.fallback_suggestions()
                    state.suggestions = block0["suggestions"]
                    show_credits_dialog(view_state.page, view_state.credit_service)
                else:
                    # Execute describe and suggest concurrently to save up to 4+ seconds of startup latency
                    description, suggestions = await asyncio.gather(
                        ai_service.describe_dataset(state.current_df_summary),
                        ai_service.suggest(state.current_df_summary),
                    )
                    block0["description"] = description
                    block0["suggestions"] = suggestions
                    state.suggestions = suggestions

                state.credits_remaining = await view_state.credit_service.get_balance()
                view_state.rebuild()

                if getattr(state, "autopilot_enabled", False):
                    await run_autopilot(view_state)

            except Exception as e:
                logger.error("Initial AI load failed: %s", e)
                block0["description"] = (
                    f"Dataset loaded ({state.current_df_rows:,} rows, "
                    f"{len(state.current_df_columns)} columns). "
                    f"AI is offline — use custom prompts to analyze."
                )
                block0["suggestions"] = ai_service.fallback_suggestions()
                state.suggestions = block0["suggestions"]
                view_state.rebuild()

        view_state.page.run_task(load_initial_ai)

    except Exception as err:
        show_error(view_state, f"Failed to load table: {err}")
        state.clear_data()
        logger.exception("DB table load error")
    finally:
        state.is_loading = False
        view_state.rebuild()
