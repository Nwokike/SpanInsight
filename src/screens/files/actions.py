"""File transfer and manipulation actions: upload, download, delete, new folder, load in analysis."""

from __future__ import annotations

import logging
import os
import posixpath

import flet as ft

from core import tokens
from core.state import state
from screens.files.components import fmt_size

logger = logging.getLogger("FilesActions")


async def handle_upload_async(
    page: ft.Page, colab, current_path: str, active_session: str, fetch_listing_fn
):
    """FilePicker dialog to upload multiple local files to Colab filesystem."""
    picker = page.file_picker
    results = await picker.pick_files(
        allow_multiple=True,
        dialog_title="Select files to upload",
    )
    if not results:
        return

    for picked in results:
        if not picked.path:
            continue
        remote_path = posixpath.join(current_path, picked.name)

        status_text = ft.Text(
            f"Uploading {picked.name}…",
            size=tokens.FONT_XS,
            color=ft.Colors.ON_SURFACE_VARIANT,
        )
        prog = ft.ProgressBar(
            color=ft.Colors.PRIMARY,
            bgcolor=ft.Colors.with_opacity(0.12, ft.Colors.PRIMARY),
        )
        dlg = ft.AlertDialog(
            title=ft.Text(
                f"Uploading {picked.name}",
                size=tokens.FONT_MD,
                weight=ft.FontWeight.W_600,
            ),
            content=ft.Column(
                [prog, status_text],
                spacing=tokens.SPACE_SM,
                tight=True,
            ),
        )
        page.show_dialog(dlg)

        try:
            await colab.upload(picked.path, remote_path, active_session)
            if page:
                page.snack_bar = ft.SnackBar(ft.Text(f"✅ Uploaded {picked.name}"))
                page.snack_bar.open = True
        except Exception as ex:
            logger.error("Upload failed: %s", ex)
            if page:
                page.snack_bar = ft.SnackBar(
                    ft.Text(f"❌ Upload failed: {ex}"),
                    bgcolor=ft.Colors.ERROR,
                )
                page.snack_bar.open = True
        finally:
            dlg.open = False
            try:
                page.update()
            except Exception:
                pass

    await fetch_listing_fn(current_path)


async def handle_download_async(
    page: ft.Page,
    colab,
    current_path: str,
    selected_files: set[str],
    listing: list[dict],
    active_session: str,
    clear_selection_fn,
):
    """Download selected files/directories locally (with mobile fallback)."""
    if not selected_files:
        return

    for item_name in list(selected_files):
        item = next((i for i in listing if i["name"] == item_name), None)
        if not item:
            continue

        is_dir = item.get("type") == "directory"
        size_str = fmt_size(item.get("size"))
        default_name = f"{item_name}.zip" if is_dir else item_name

        if page.platform.is_mobile():
            dl_dir = "/storage/emulated/0/Download"
            if not os.path.exists(dl_dir):
                dl_dir = os.path.join(os.path.expanduser("~"), "Downloads")
            os.makedirs(dl_dir, exist_ok=True)
            name_part, ext_part = os.path.splitext(default_name)
            counter = 1
            local_path = os.path.join(dl_dir, default_name)
            while os.path.exists(local_path):
                local_path = os.path.join(dl_dir, f"{name_part} ({counter}){ext_part}")
                counter += 1
        else:
            try:
                local_path = await page.file_picker.save_file(
                    dialog_title=f"Save {default_name}",
                    file_name=default_name,
                )
            except ValueError:
                dl_dir = os.path.join(os.path.expanduser("~"), "Downloads")
                os.makedirs(dl_dir, exist_ok=True)
                local_path = os.path.join(dl_dir, default_name)

        if not local_path:
            continue

        status_text = ft.Text(
            f"Downloading…{(' ' + size_str) if size_str else ''}",
            size=tokens.FONT_XS,
            color=ft.Colors.ON_SURFACE_VARIANT,
        )
        prog = ft.ProgressBar(
            color=ft.Colors.PRIMARY,
            bgcolor=ft.Colors.with_opacity(0.12, ft.Colors.PRIMARY),
        )
        dlg = ft.AlertDialog(
            title=ft.Text(
                f"Downloading {default_name}",
                size=tokens.FONT_MD,
                weight=ft.FontWeight.W_600,
            ),
            content=ft.Column(
                [prog, status_text],
                spacing=tokens.SPACE_SM,
                tight=True,
            ),
        )
        page.show_dialog(dlg)

        def _on_status(msg: str, _st=status_text):
            _st.value = msg
            try:
                _st.update()
            except Exception:
                pass

        try:
            remote_path = posixpath.join(current_path, item_name)
            if is_dir:
                await colab.download_folder(
                    remote_path, local_path, active_session, on_status=_on_status
                )
            else:
                await colab.download(remote_path, local_path, active_session)
            if page:
                page.snack_bar = ft.SnackBar(ft.Text(f"✅ Saved to {local_path}"))
                page.snack_bar.open = True
        except Exception as ex:
            logger.error("Download failed: %s", ex)
            if page:
                page.snack_bar = ft.SnackBar(
                    ft.Text(f"❌ Download failed: {ex}"),
                    bgcolor=ft.Colors.ERROR,
                )
                page.snack_bar.open = True
        finally:
            dlg.open = False
            try:
                page.update()
            except Exception:
                pass

    clear_selection_fn()


def handle_load_in_analysis(page: ft.Page, current_path: str, item_name: str):
    """Generate appropriate pandas read_* Python code and navigate to Analysis tab."""
    remote_path = posixpath.join(current_path, item_name)
    _, ext = os.path.splitext(item_name.lower())

    if ext in (".csv", ".tsv"):
        code = (
            f"import pandas as pd\n"
            f"df = pd.read_csv('{remote_path}')\n"
            f"print(f'Loaded {{len(df):,}} rows × {{len(df.columns)}} columns')\n"
            f"df.head()"
        )
    elif ext in (".xlsx", ".xls"):
        code = (
            f"import pandas as pd\n"
            f"df = pd.read_excel('{remote_path}')\n"
            f"print(f'Loaded {{len(df):,}} rows × {{len(df.columns)}} columns')\n"
            f"df.head()"
        )
    elif ext == ".json":
        code = (
            f"import pandas as pd\n"
            f"df = pd.read_json('{remote_path}')\n"
            f"print(f'Loaded {{len(df):,}} rows × {{len(df.columns)}} columns')\n"
            f"df.head()"
        )
    elif ext == ".parquet":
        code = (
            f"import pandas as pd\n"
            f"df = pd.read_parquet('{remote_path}')\n"
            f"print(f'Loaded {{len(df):,}} rows × {{len(df.columns)}} columns')\n"
            f"df.head()"
        )
    else:
        code = f"import pandas as pd\ndf = pd.read_csv('{remote_path}')\ndf.head()"

    state.add_cell("code", code)
    state.current_tab = 1
    if page:
        page.snack_bar = ft.SnackBar(
            ft.Text(f"Added load cell for {item_name} → Analysis")
        )
        page.snack_bar.open = True
        page.update()


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
            page.snack_bar = ft.SnackBar(
                ft.Text(f"❌ Some deletes failed:\n{chr(10).join(failed)}"),
                bgcolor=ft.Colors.ERROR,
            )
            page.snack_bar.open = True
    else:
        if page:
            page.snack_bar = ft.SnackBar(ft.Text(f"✅ Deleted {len(names)} item(s)"))
            page.snack_bar.open = True

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
            page.snack_bar = ft.SnackBar(ft.Text(f"✅ Created: {name}"))
            page.snack_bar.open = True
    except Exception as ex:
        if page:
            page.snack_bar = ft.SnackBar(ft.Text(f"❌ {ex}"), bgcolor=ft.Colors.ERROR)
            page.snack_bar.open = True
    await fetch_listing_fn(current_path)


async def handle_inspect_dataset_async(
    page: ft.Page,
    colab,
    current_path: str,
    item_name: str,
    active_session: str,
):
    """Fetches fast schema snapshot and opens Dataset Inspector modal."""
    import json

    from components.dataset_inspector import show_dataset_inspector

    full_path = posixpath.join(current_path, item_name)
    inspect_code = (
        f"import json, pandas as pd\n"
        f"try:\n"
        f"    df = pd.read_csv('{full_path}') if '{item_name}'.endswith('.csv') else pd.read_excel('{full_path}')\n"
        f"    schema = {{\n"
        f"        'shape': [int(df.shape[0]), int(df.shape[1])],\n"
        f"        'columns': list(df.columns),\n"
        f"        'dtypes': {{str(col): str(dtype) for col, dtype in df.dtypes.items()}},\n"
        f"        'summary': {{str(col): {{'mean': float(df[col].mean()), 'min': float(df[col].min()), 'max': float(df[col].max())}} for col in df.select_dtypes(include=['number']).columns[:10]}}\n"
        f"    }}\n"
        f"    print('__SCHEMA_START__' + json.dumps(schema) + '__SCHEMA_END__')\n"
        f"except Exception as e:\n"
        f"    print('ERR:' + str(e))\n"
    )
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
