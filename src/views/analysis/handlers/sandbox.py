import asyncio
import logging

from core.state import state
from core.utils import figure_to_png_bytes
from services import sandbox

from .base import show_error, show_success

logger = logging.getLogger(__name__)


async def on_rerun_code(view_state, block_index: int, new_code: str):
    if block_index < 0 or block_index >= len(state.analysis_blocks):
        return

    block = state.analysis_blocks[block_index]
    result = await sandbox.execute_code_async(new_code, state.current_df)

    block["code"] = new_code
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
        figure_png = None
        if raw_figure:
            try:
                figure_png = await asyncio.to_thread(figure_to_png_bytes, raw_figure)
            except Exception:
                pass

        block["figure"] = None
        block["figure_png"] = figure_png
        block["stdout"] = result.get("stdout", "")
        block["result"] = result.get("result", "")
        block["description"] = "Code re-executed successfully."
        block["failed"] = False
        show_success(view_state, "✅ Code re-executed successfully!")
    else:
        block["description"] = f"Execution failed: {result['error']}"
        block["failed"] = True
        show_error(view_state, f"Execution Error: {result['error']}")

    view_state.rebuild()
