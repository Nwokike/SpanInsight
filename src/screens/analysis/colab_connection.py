"""Colab session connection, authentication, and VM recovery operations."""

from __future__ import annotations

import logging

import flet as ft

from core.state import state
from core.utils import show_snack
from screens.analysis.bootstrap import setup_colab_environment

logger = logging.getLogger("ColabConnection")


def session_expired(msg: str) -> bool:
    """Check whether an execution error indicates a dead/expired Colab VM."""
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


async def connect_colab_async(colab, page: ft.Page | None, set_is_connecting):
    """Start or verify Colab VM session."""
    set_is_connecting(True)
    try:
        auth_result = await colab.check_auth()
        if not auth_result.get("authenticated"):
            if page:
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

        is_dark = (
            state.theme_mode == ft.ThemeMode.DARK
            if hasattr(state, "theme_mode")
            else False
        )
        await setup_colab_environment(colab, state.active_session_name, is_dark=is_dark)

        if page:
            show_snack(
                page,
                f"Connected - {state.session_hardware} session ready",
                success=True,
            )
    except Exception as e:
        logger.error("Connect failed: %s", e)
        if page:
            show_snack(page, f"Connection failed: {e}", error=True)
    finally:
        set_is_connecting(False)


async def recover_session_async(colab, page: ft.Page | None) -> None:
    """Rebuild a dead Colab session: new session → theme bootstrap → cached dataset reload."""
    await connect_colab_async(colab, page, lambda _v: None)
    if not state.active_session_name:
        raise RuntimeError("No active session after reconnect")

    try:
        await ensure_active_dataset_in_kernel(colab, state.active_session_name)
    except Exception as ex:
        logger.warning("Cached dataset reload after reconnect failed: %s", ex)
