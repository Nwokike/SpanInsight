import asyncio
import logging
import flet as ft

from core.state import state
from core import theme
from services import file_service
from services import dataset_cache
from .base import show_error

logger = logging.getLogger(__name__)


def on_clear_data(view_state, e):
    import matplotlib.pyplot as plt

    plt.close("all")
    dataset_cache.delete_cache(state.active_project_id)
    state.clear_data()
    state.analysis_blocks.clear()
    view_state.rebuild()


async def on_export_data(view_state, export_format: str = "csv"):
    if state.current_df is None:
        show_error(view_state, "No active dataset to export.")
        return

    view_state.page.snack_bar = ft.SnackBar(
        ft.Text(f"Preparing {export_format.upper()} export..."), duration=2000
    )
    view_state.page.snack_bar.open = True
    view_state.page.update()

    try:
        if view_state.page.platform in (ft.PagePlatform.ANDROID, ft.PagePlatform.IOS):
            try:
                import flet_ads as fta

                async def _show_ad(e):
                    await e.control.show()

                fta.InterstitialAd(
                    unit_id="ca-app-pub-5679949845754640/6965536622",
                    on_load=lambda e: view_state.page.run_task(_show_ad, e),
                    on_error=lambda e: logger.error(
                        "Export Interstitial error: %s", e.data
                    ),
                )
            except Exception as ad_err:
                logger.error("Export Interstitial trigger failed: %s", ad_err)

        base_name = state.current_df_name or "cleaned_dataset"
        base_name = base_name.rsplit(".", 1)[0]

        if export_format == "csv":
            file_bytes = await asyncio.to_thread(
                file_service.df_to_csv_bytes, state.current_df
            )
            suggested_name = f"{base_name}_cleaned.csv"
            allowed_ext = ["csv"]
        elif export_format == "xlsx":
            file_bytes = await asyncio.to_thread(
                file_service.df_to_styled_excel_bytes, state.current_df, base_name
            )
            suggested_name = f"{base_name}_styled.xlsx"
            allowed_ext = ["xlsx"]
        else:
            show_error(view_state, f"Unsupported export format: {export_format}")
            return

        res = await view_state.file_picker_svc.save_file_async(
            file_name=suggested_name,
            allowed_extensions=allowed_ext,
            src_bytes=file_bytes,
        )

        if res:
            view_state.page.snack_bar = ft.SnackBar(
                ft.Text(f"✓ {export_format.upper()} saved successfully!"),
                bgcolor=theme.SUCCESS,
                duration=3000,
            )
        else:
            view_state.page.snack_bar = ft.SnackBar(
                ft.Text("Save cancelled by user."),
                duration=2000,
            )
        view_state.page.snack_bar.open = True
        view_state.page.update()

    except Exception as e:
        logger.error("Failed to export dataset: %s", e)
        show_error(view_state, f"Export failed: {e}")
