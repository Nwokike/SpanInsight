"""Dynamic patcher to redirect colab_cli and app storage paths for Flet/Android consistency."""

from __future__ import annotations

import logging
import os
from pathlib import Path

logger = logging.getLogger("storage_patch")


def resolve_storage_dir() -> Path:
    """Return the canonical storage directory path.

    On mobile the sandbox path (FLET_APP_STORAGE_DATA) is used.
    On desktop the '.flet/storage/data' folder is used.
    All services call this so they never diverge.
    """
    storage_env = os.getenv("FLET_APP_STORAGE_DATA")
    if storage_env:
        return Path(storage_env)
    project_root = Path(__file__).resolve().parent.parent.parent
    return project_root / ".flet" / "storage" / "data"


def resolve_cache_dir() -> Path:
    """Return the canonical cache directory path."""
    cache_env = os.getenv("FLET_APP_STORAGE_CACHE")
    if cache_env:
        return Path(cache_env)
    project_root = Path(__file__).resolve().parent.parent.parent
    return project_root / ".flet" / "storage" / "cache"


def resolve_temp_dir() -> Path:
    """Return the canonical temp directory path."""
    temp_env = os.getenv("FLET_APP_STORAGE_TEMP")
    if temp_env:
        return Path(temp_env)
    project_root = Path(__file__).resolve().parent.parent.parent
    return project_root / ".flet" / "storage" / "temp"


def apply_storage_patches() -> None:
    """Apply storage redirections and mobile compatibility shims."""
    storage_dir = resolve_storage_dir()
    os.makedirs(storage_dir, exist_ok=True)

    import sys
    import types

    # 1. Flet Android engine strips 'wsgiref' which google_auth_oauthlib depends on.
    # We do not run local servers on Android, so provide safe mock stubs.
    if "wsgiref" not in sys.modules:
        wsgiref = types.ModuleType("wsgiref")
        sys.modules["wsgiref"] = wsgiref

        wsgiref_util = types.ModuleType("wsgiref.util")
        sys.modules["wsgiref.util"] = wsgiref_util
        wsgiref_util.request_uri = lambda *a, **k: ""
        wsgiref.util = wsgiref_util

        wsgiref_simple_server = types.ModuleType("wsgiref.simple_server")
        sys.modules["wsgiref.simple_server"] = wsgiref_simple_server

        class MockWSGIRequestHandler:
            pass

        class MockWSGIServer:
            allow_reuse_address = False

        wsgiref_simple_server.WSGIRequestHandler = MockWSGIRequestHandler
        wsgiref_simple_server.WSGIServer = MockWSGIServer
        wsgiref_simple_server.make_server = lambda *a, **k: None
        wsgiref.simple_server = wsgiref_simple_server

    # 2. Ensure jupyter_kernel_client modules/stubs are safe
    if "jupyter_kernel_client" not in sys.modules:
        try:
            import jupyter_kernel_client  # noqa: F401
        except ImportError:

            def _make_stub_module(fullname: str):
                mod = types.ModuleType(fullname)
                sys.modules[fullname] = mod
                return mod

            _make_stub_module("jupyter_kernel_client")

    ctx = sys.modules.get("jupyter_kernel_client")
    if ctx is not None:
        # colab_cli expects KernelClient which jupyter_kernel_client exports as JupyterKernelClient
        if (
            not hasattr(ctx, "KernelClient")
            or getattr(ctx, "KernelClient", None) is None
        ) and hasattr(ctx, "JupyterKernelClient"):
            ctx.KernelClient = ctx.JupyterKernelClient

        if (
            not hasattr(ctx, "JupyterSubprotocol")
            or getattr(ctx, "JupyterSubprotocol", None) is None
        ):
            import enum

            class MockJupyterSubprotocol(enum.Enum):
                DEFAULT = "v1.kernel.websocket.jupyter.org"

            ctx.JupyterSubprotocol = MockJupyterSubprotocol

        if "jupyter_kernel_client.wsclient" not in sys.modules:
            wsclient_mod = types.ModuleType("jupyter_kernel_client.wsclient")
            sys.modules["jupyter_kernel_client.wsclient"] = wsclient_mod
            ctx.wsclient = wsclient_mod
            wsclient_mod.JupyterSubprotocol = ctx.JupyterSubprotocol

    # 3. Patch colab_cli modules to use canonical storage_dir
    try:
        import colab_cli.auth
        import colab_cli.common
        import colab_cli.history
        import colab_cli.state

        # Override token path
        colab_cli.auth.TOKEN_CONFIG_PATH = str(storage_dir / "token.json")

        # Patch State.__init__ so every new State instance gets the correct paths
        original_state_init = colab_cli.common.State.__init__

        def patched_state_init(self, *args, **kwargs):
            original_state_init(self, *args, **kwargs)
            self.config_path = str(storage_dir / "sessions.json")
            self.client_oauth_config = str(storage_dir / "oauth_config.json")

        colab_cli.common.State.__init__ = patched_state_init

        # Override HistoryLogger init
        original_history_init = colab_cli.history.HistoryLogger.__init__
        canonical_history_dir = str(storage_dir / "history")
        os.makedirs(canonical_history_dir, exist_ok=True)

        def patched_history_init(
            self, log_dir: str = "~/.config/colab-cli/history", *args, **kwargs
        ):
            if (
                not log_dir
                or log_dir == "~/.config/colab-cli/history"
                or log_dir == os.path.expanduser("~/.config/colab-cli/history")
            ):
                log_dir = canonical_history_dir
            original_history_init(self, log_dir, *args, **kwargs)

        colab_cli.history.HistoryLogger.__init__ = patched_history_init

        # Override SettingsStore and StateStore default paths
        colab_cli.state.SettingsStore.__init__.__defaults__ = (
            str(storage_dir / "settings.json"),
        )
        colab_cli.state.StateStore.__init__.__defaults__ = (
            str(storage_dir / "sessions.json"),
        )

        logger.info("Storage patches applied successfully -> %s", storage_dir)
    except ImportError as e:
        logger.warning("colab_cli not available to patch: %s", e)

    # 4. Defensive patches to eliminate write() str vs bytes TypeErrors
    try:
        from rich.file_proxy import FileProxy

        _orig_fp_write = FileProxy.write

        def patched_fp_write(self, text):
            if isinstance(text, bytes):
                text = text.decode("utf-8", errors="ignore")
            elif not isinstance(text, str):
                text = str(text)
            return _orig_fp_write(self, text)

        FileProxy.write = patched_fp_write
    except ImportError:
        pass

    try:
        from colab_cli.state import _LockedFileStore

        _orig_write_data = _LockedFileStore._write_data

        def patched_write_data(self, f, data):
            if isinstance(data, bytes):
                data = data.decode("utf-8", errors="ignore")
            elif not isinstance(data, str):
                data = str(data)
            return _orig_write_data(self, f, data)

        _LockedFileStore._write_data = patched_write_data
    except Exception:
        pass
