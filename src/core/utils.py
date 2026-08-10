"""Shared utilities — snackbar, version comparison, image helpers."""

from __future__ import annotations

import base64
import logging
from pathlib import Path

import flet as ft

logger = logging.getLogger(__name__)


def show_snack(
    page: ft.Page,
    message: str,
    *,
    error: bool = False,
    success: bool = False,
    duration: int = 3000,
) -> None:
    """Show a styled snackbar notification.

    Args:
        page: The Flet page instance.
        message: Text to display.
        error: If True, show with red error styling.
        success: If True, show with green success styling.
        duration: Display duration in milliseconds.
    """
    from core import theme

    bgcolor = None
    text_color = None
    if error:
        bgcolor = theme.ERROR
        text_color = ft.Colors.WHITE
    elif success:
        bgcolor = theme.SUCCESS
        text_color = ft.Colors.WHITE

    page.snack_bar = ft.SnackBar(
        content=ft.Text(message, color=text_color),
        bgcolor=bgcolor,
        duration=duration,
    )
    page.snack_bar.open = True
    page.update()


def parse_version(version_str: str) -> tuple[int, ...]:
    """Parse a semver string into a comparable tuple.

    >>> parse_version("1.2.3")
    (1, 2, 3)
    >>> parse_version("10.0.0") > parse_version("9.9.9")
    True
    """
    try:
        return tuple(int(x) for x in version_str.strip().split("."))
    except ValueError, AttributeError:
        return (0, 0, 0)


def png_bytes_to_base64(png_bytes: bytes) -> str:
    """Encode PNG bytes as a base64 string for ft.Image(src_base64=...)."""
    return base64.b64encode(png_bytes).decode("utf-8")


def figure_to_png_bytes(fig) -> bytes:
    """Convert a matplotlib Figure to PNG bytes.

    Args:
        fig: A matplotlib.figure.Figure instance.

    Returns:
        PNG image as bytes.
    """
    import io

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150, bbox_inches="tight", transparent=True)
    buf.seek(0)
    return buf.read()


def get_temp_dir() -> Path:
    """Resolve a writeable temporary directory safely across desktop and mobile platforms."""
    import os
    from pathlib import Path

    # 1. Try Flet's dedicated temporary storage directory environment variable (Android/iOS sandbox)
    temp_env = os.getenv("FLET_APP_STORAGE_TEMP")
    if temp_env:
        path = Path(temp_env)
        try:
            path.mkdir(parents=True, exist_ok=True)
            return path
        except Exception:
            pass

    # 2. Fall back to standard OS-specific temporary path or application base path
    try:
        path = Path.home() / ".spaninsight" / "temp"
        path.mkdir(parents=True, exist_ok=True)
        return path
    except Exception:
        # 3. Absolute last resort fallback (local directory in app space)
        fallback_path = Path("./.temp_cache")
        fallback_path.mkdir(parents=True, exist_ok=True)
        return fallback_path


def get_banner_ad(unit_id: str, width: int = 320, height: int = 50) -> ft.Control:
    """Instantiate flet_ads.BannerAd safely.

    If flet_ads fails to load (e.g. unsupported on Web/PC or dynamic linking issues),
    gracefully returns an empty ft.Container() instead of crashing the view.
    """
    try:
        import flet_ads as fta

        return fta.BannerAd(unit_id=unit_id, width=width, height=height)
    except Exception as e:
        logger.warning("Failed to load BannerAd (using safe fallback Container): %s", e)
        return ft.Container()


def sanitize_output(val):
    """Replace NaN/Infinity with None recursively in nested structures.

    Used to sanitize Colab execution output before JSON serialization.
    """
    import math

    if isinstance(val, list):
        return [sanitize_output(v) for v in val]
    if isinstance(val, dict):
        return {k: sanitize_output(v) for k, v in val.items()}
    if isinstance(val, float) and (math.isnan(val) or math.isinf(val)):
        return None
    return val


def sanitize_numpy(val):
    """Recursively convert numpy types to Python natives for JSON serialization."""
    try:
        import numpy as np

        if isinstance(val, np.integer):
            return int(val)
        if isinstance(val, np.floating):
            return float(val) if not np.isnan(val) else None
        if isinstance(val, np.ndarray):
            return [sanitize_numpy(v) for v in val.tolist()]
        if isinstance(val, np.bool_):
            return bool(val)
    except ImportError:
        pass

    if isinstance(val, list):
        return [sanitize_numpy(v) for v in val]
    if isinstance(val, dict):
        return {k: sanitize_numpy(v) for k, v in val.items()}
    return val
