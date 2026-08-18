"""Shared utilities — snackbar, version comparison, image helpers."""

from __future__ import annotations

import base64
import logging
from pathlib import Path

import flet as ft

logger = logging.getLogger(__name__)


def show_snack(
    page: ft.Page | None,
    message: str,
    *,
    error: bool = False,
    success: bool = False,
    duration: int = 3000,
) -> None:
    """Show a styled snackbar notification using Flet 0.86+ DialogControl API.

    Args:
        page: The Flet page instance.
        message: Text to display.
        error: If True, show with red error styling.
        success: If True, show with green success styling.
        duration: Display duration in milliseconds.
    """
    if not page:
        return

    from core import theme

    bgcolor = None
    text_color = None
    if error:
        bgcolor = theme.ERROR
        text_color = ft.Colors.WHITE
    elif success:
        bgcolor = theme.SUCCESS
        text_color = ft.Colors.WHITE

    snack = ft.SnackBar(
        content=ft.Text(message, color=text_color),
        bgcolor=bgcolor,
        duration=duration,
    )
    try:
        page.show_dialog(snack)
    except Exception as ex:
        logger.warning("Failed to show snack dialog: %s", ex)


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
    """Encode PNG bytes as a base64 string for ft.Image(src=...)."""
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
    """Resolve a writeable temporary directory using Flet's app storage paths."""
    import os
    from pathlib import Path

    # FLET_APP_STORAGE_TEMP is always set by Flet at runtime (→ .flet/storage/temp/ locally,
    # app private temp dir on Android)
    temp_env = os.getenv("FLET_APP_STORAGE_TEMP")
    if temp_env:
        path = Path(temp_env)
    else:
        # Dev fallback — matches the .flet folder structure Flet creates locally
        path = Path(".flet") / "storage" / "temp"

    try:
        path.mkdir(parents=True, exist_ok=True)
        return path
    except Exception:
        # Absolute last resort
        fallback = Path(".temp_cache")
        fallback.mkdir(parents=True, exist_ok=True)
        return fallback


def get_banner_ad(
    unit_id: str | None = None, width: int = 320, height: int = 50
) -> ft.Control:
    """Instantiate flet_ads.BannerAd safely.

    If flet_ads fails to load (e.g. unsupported on Web/PC or dynamic linking issues),
    gracefully returns an empty ft.Container() instead of crashing the view.
    """
    from core.constants import ADMOB_BANNER_ID

    effective_unit_id = unit_id or ADMOB_BANNER_ID
    try:
        import flet_ads as fta

        return fta.BannerAd(unit_id=effective_unit_id, width=width, height=height)
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
    """Recursively convert numpy and float types to Python natives for JSON serialization."""
    import math

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

    if isinstance(val, float) and (math.isnan(val) or math.isinf(val)):
        return None
    if isinstance(val, list):
        return [sanitize_numpy(v) for v in val]
    if isinstance(val, dict):
        return {k: sanitize_numpy(v) for k, v in val.items()}
    return val


def build_analysis_context(
    cells: list[dict], max_cells: int = 6, max_chars: int = 2500
) -> str:
    """Compact 'recent work' context for AI prompts.

    Long notebooks used to inflate suggest/code prompts (10K+ chars observed
    live), multiplying gateway latency on reasoning models. Only the most
    recent code steps matter for "do NOT repeat" guidance.
    """
    steps = []
    for c in cells or []:
        if c.get("type") != "code":
            continue
        step = (c.get("prompt") or c.get("source", "")[:80] or "").strip()
        if step:
            steps.append(step)
    ctx = "\n".join(steps[-max_cells:])
    if len(ctx) > max_chars:
        ctx = "…\n" + ctx[-max_chars:]
    return ctx
