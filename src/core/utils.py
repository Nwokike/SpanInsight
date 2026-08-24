"""Shared utilities - snackbar, version comparison, image helpers."""

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


async def set_clipboard(_page: ft.Page | None, text: str) -> bool:
    """Safely copy string text to system clipboard in Flet 0.86+.

    Args:
        _page: The Flet page instance (optional).
        text: The string to store on the clipboard.

    Returns:
        True if copied successfully, False otherwise.
    """
    if not text:
        return False
    try:
        await ft.Clipboard().set(text)
        return True
    except Exception as ex:
        logger.error("Failed to copy to clipboard: %s", ex)
        return False


async def resolve_save_path(page: ft.Page | None, default_name: str) -> str | None:
    """Resolve destination file save path across Android/iOS mobile and desktop platforms.

    - On mobile (Android/iOS): saves directly to /storage/emulated/0/Download or ~/Downloads.
    - On desktop: prompts the user via FilePicker.save_file dialog, falling back to ~/Downloads.
    """
    import os

    is_mobile = False
    if page and hasattr(page, "platform"):
        is_mobile = page.platform in (
            ft.PagePlatform.ANDROID,
            getattr(ft.PagePlatform, "ANDROID_TV", ft.PagePlatform.ANDROID),
            ft.PagePlatform.IOS,
        )

    if is_mobile:
        dl_dir = "/storage/emulated/0/Download"
        if not os.path.exists(dl_dir):
            dl_dir = os.path.join(os.path.expanduser("~"), "Downloads")
        os.makedirs(dl_dir, exist_ok=True)

        name_part, ext_part = os.path.splitext(default_name)
        counter = 1
        unique_name = default_name
        while os.path.exists(os.path.join(dl_dir, unique_name)):
            unique_name = f"{name_part} ({counter}){ext_part}"
            counter += 1
        return os.path.join(dl_dir, unique_name)

    # Desktop: try native file_picker
    file_picker = getattr(page, "file_picker", None) if page else None
    if not file_picker and page:
        file_picker = ft.FilePicker()
        page.services.append(file_picker)
        try:
            page.update()
        except Exception:
            pass

    path = None
    if file_picker:
        try:
            path = await file_picker.save_file(
                dialog_title=f"Save {default_name}",
                file_name=default_name,
            )
        except Exception as ex:
            logger.debug("FilePicker save_file canceled or failed: %s", ex)
            path = None

    if not path:
        dl_dir = os.path.join(os.path.expanduser("~"), "Downloads")
        os.makedirs(dl_dir, exist_ok=True)
        name_part, ext_part = os.path.splitext(default_name)
        counter = 1
        unique_name = default_name
        while os.path.exists(os.path.join(dl_dir, unique_name)):
            unique_name = f"{name_part} ({counter}){ext_part}"
            counter += 1
        path = os.path.join(dl_dir, unique_name)

    return path


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
    from core.storage_patch import resolve_temp_dir

    path = resolve_temp_dir()
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

    BannerAd raises FletUnsupportedPlatformException in before_update() on any
    non-mobile platform, so we must never return a real instance off-mobile.
    We resolve the current page from the render context and return an empty
    Container unless we are on Android/iOS. If flet_ads fails to load, we also
    fall back to an empty Container instead of crashing the view.
    """
    from core.constants import ADMOB_BANNER_ID

    # Only render a real ad on mobile; BannerAd throws on desktop/web at render.
    try:
        page = ft.context.page
        if page is None or page.web or not page.platform.is_mobile():
            return ft.Container()
    except Exception:
        # No render context (e.g. called outside a component) - stay safe.
        return ft.Container()

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
    cells: list[dict],
    max_cells: int = 6,
    max_chars: int = 2500,
    findings_context: str = "",
) -> str:
    """Compact 'recent work' context for AI prompts, plus protected findings.

    Long notebooks used to inflate suggest/code prompts (10K+ chars observed
    live), multiplying gateway latency on reasoning models. Only the most
    recent code steps matter for "do NOT repeat" guidance. Verified findings
    get their own 1200-char budget prepended, so past knowledge can never be
    clipped by the recency truncation.
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

    findings_block = ""
    fb = (findings_context or "").strip()
    if fb:
        if len(fb) > 1200:
            fb = fb[:1200]
        findings_block = (
            "VERIFIED FINDINGS (established facts about this data):\n" + fb + "\n\n"
        )

    return findings_block + ctx


def build_findings_context(findings: list[dict]) -> str:
    """Format verified findings for prompt injection (bounded by caller)."""
    lines = []
    for f in (findings or [])[:8]:
        text = str(f.get("text") or "").strip()
        if not text:
            continue
        nums = f.get("key_numbers") or []
        line = f"• {text}"
        if nums:
            line += f" [{'; '.join(str(n) for n in nums[:3])}]"
        lines.append(line)
    return "\n".join(lines)
