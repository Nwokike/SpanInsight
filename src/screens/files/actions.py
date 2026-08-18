"""Action handlers for Files screen: upload, download, delete, new folder, and inspector."""

from __future__ import annotations

import logging
import posixpath

import flet as ft

from core import tokens
from core.state import state
from core.utils import show_snack

logger = logging.getLogger("FilesActions")


async def handle_upload_async(
    page: ft.Page,
    colab,
    current_path: str,
    active_session: str,
    fetch_listing_fn,
):
    """Opens FilePicker, uploads selected file to Colab current_path with progress."""
    picker = page.file_picker
    result = await picker.pick_files(
        allow_multiple=False,
        dialog_title="Upload File to Colab Session",
    )
    if not result or not result[0].path:
        return

    picked = result[0]
    remote_path = posixpath.join(current_path, picked.name)

    prog = ft.ProgressBar(width=280)
    status_text = ft.Text(f"Uploading {picked.name}…", size=tokens.FONT_SM)
    dlg = ft.AlertDialog(
        title=ft.Text("Uploading File", size=tokens.FONT_MD),
        content=ft.Column(
            controls=[prog, status_text],
            spacing=tokens.SPACE_SM,
            tight=True,
        ),
    )
    page.show_dialog(dlg)

    try:
        await colab.upload(picked.path, remote_path, active_session)
        if page:
            show_snack(page, f"✅ Uploaded {picked.name}", success=True)
    except Exception as ex:
        logger.error("Upload failed: %s", ex)
        if page:
            show_snack(page, f"❌ Upload failed: {ex}", error=True)
    finally:
        try:
            page.pop_dialog()
        except Exception:
            pass

    await fetch_listing_fn(current_path)


async def handle_download_async(
    page: ft.Page,
    colab,
    current_path: str,
    selected_files: set[str],
    active_session: str,
    listing: list[dict],
    clear_selection_fn,
):
    """Downloads selected files/folders to local storage."""
    if not selected_files:
        return

    from services.storage_service import _STORAGE_DIR

    downloads_dir = _STORAGE_DIR / "downloads"
    downloads_dir.mkdir(parents=True, exist_ok=True)

    items_by_name = {item.get("name"): item for item in listing}

    for name in list(selected_files):
        item_info = items_by_name.get(name, {})
        is_dir = item_info.get("is_dir", False)
        remote_path = posixpath.join(current_path, name)
        local_path = str(downloads_dir / name)

        prog = ft.ProgressBar(width=280)
        status_text = ft.Text(f"Downloading {name}…", size=tokens.FONT_SM)
        dlg = ft.AlertDialog(
            title=ft.Text("Downloading", size=tokens.FONT_MD),
            content=ft.Column(
                controls=[prog, status_text],
                spacing=tokens.SPACE_SM,
                tight=True,
            ),
        )
        page.show_dialog(dlg)

        def _on_status(msg: str, st=status_text):
            st.value = msg
            try:
                page.update()
            except Exception:
                pass

        try:
            if is_dir:
                await colab.download_folder(
                    remote_path, local_path, active_session, on_status=_on_status
                )
            else:
                await colab.download(remote_path, local_path, active_session)
            if page:
                show_snack(page, f"✅ Saved to {local_path}", success=True)
        except Exception as ex:
            logger.error("Download failed: %s", ex)
            if page:
                show_snack(page, f"❌ Download failed: {ex}", error=True)
        finally:
            try:
                page.pop_dialog()
            except Exception:
                pass

    clear_selection_fn()


def handle_load_in_analysis(page: ft.Page, current_path: str, item_name: str):
    """Hand the remote file to the Analysis import pipeline (load + schema + AI)."""
    remote_path = posixpath.join(current_path, item_name)
    state.pending_dataset_load = {"remote_path": remote_path, "name": item_name}
    state.current_tab = 1
    if page:
        show_snack(page, f"Loading {item_name} → Analysis")


async def do_delete_async(
    page: ft.Page,
    colab,
    current_path: str,
    names: list[str],
    active_session: str,
    set_is_loading,
    clear_selection_fn,
    fetch_listing_fn,
):
    """Deletes list of file names from active session."""
    set_is_loading(True)
    failed = []
    for name in names:
        try:
            await colab.rm(posixpath.join(current_path, name), active_session)
        except Exception as ex:
            failed.append(f"{name}: {ex}")

    if failed:
        if page:
            show_snack(
                page, f"❌ Some deletes failed:\n{chr(10).join(failed)}", error=True
            )
    else:
        if page:
            show_snack(page, f"✅ Deleted {len(names)} item(s)", success=True)

    clear_selection_fn()
    await fetch_listing_fn(current_path)


async def do_new_folder_async(
    page: ft.Page,
    colab,
    current_path: str,
    name: str,
    active_session: str,
    set_is_loading,
    fetch_listing_fn,
):
    """Creates a new folder on the Colab filesystem."""
    if not name.strip():
        return
    set_is_loading(True)
    try:
        folder_path = posixpath.join(current_path, name.strip())
        await colab.exec_code(
            f"import os; os.makedirs('{folder_path}', exist_ok=True)",
            active_session,
        )
        if page:
            show_snack(page, f"✅ Created: {name}", success=True)
    except Exception as ex:
        if page:
            show_snack(page, f"❌ {ex}", error=True)
    await fetch_listing_fn(current_path)


async def handle_inspect_dataset_async(
    page: ft.Page,
    colab,
    current_path: str,
    item_name: str,
    active_session: str,
):
    """Fetches fast schema snapshot and opens Dataset Inspector modal for any supported format."""
    import json

    from components.dataset_inspector import show_dataset_inspector
    from services.file_service import suggest_load_code

    load_stmt = suggest_load_code(item_name)
    inspect_code = f"""
import json, math
def _si_clean(v):
    if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
        return None
    if isinstance(v, dict):
        return {{str(k): _si_clean(x) for k, x in v.items()}}
    if isinstance(v, (list, tuple)):
        return [_si_clean(x) for x in v]
    return v

try:
{load_stmt}
    _cand = globals().get('df', globals().get('result', globals().get('data')))
    if _cand is not None and hasattr(_cand, 'columns') and hasattr(_cand, 'dtypes'):
        try:
            _raw_sum = _cand.describe(include='all').to_dict()
        except Exception:
            _raw_sum = _cand.describe().to_dict()
        schema = {{
            'shape': [int(_cand.shape[0]), int(_cand.shape[1])],
            'columns': [str(c) for c in _cand.columns],
            'dtypes': {{str(col): str(dtype) for col, dtype in _cand.dtypes.items()}},
            'nulls': {{str(k): int(v) for k, v in _cand.isnull().sum().items()}},
            'summary': _si_clean(_raw_sum),
        }}
        print('__SCHEMA_START__' + json.dumps(schema, default=str) + '__SCHEMA_END__')
    else:
        print('ERR:No tabular dataframe extracted')
except Exception as e:
    print('ERR:' + str(e))
"""
    try:
        res = await colab.exec_code(inspect_code, active_session)
        text = res.get("text", "")
        if "__SCHEMA_START__" in text and "__SCHEMA_END__" in text:
            raw = text.split("__SCHEMA_START__")[1].split("__SCHEMA_END__")[0]
            schema = json.loads(raw)
            show_dataset_inspector(
                page,
                dataset_name=item_name,
                schema=schema,
                on_load_in_analysis=lambda: handle_load_in_analysis(
                    page, current_path, item_name
                ),
            )
            return
    except Exception as e:
        logger.warning("Inspect failed: %s", e)

    # Fallback to load directly in analysis
    handle_load_in_analysis(page, current_path, item_name)
